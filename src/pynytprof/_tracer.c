#include <Python.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <stdatomic.h>
#include <limits.h>
#ifndef _WIN32
#include <fnmatch.h>
#include <unistd.h>
#else
#include <windows.h>
#include <Shlwapi.h>
#endif

/* ring slot record */
typedef struct {
    uint32_t line;
    uint32_t calls;
    uint64_t inc_ns;
    uint64_t exc_ns;
} Rec;

#define RING_SIZE (64 * 1024)
#define TICKS_PER_SEC 10000000ULL

static Rec *ring = NULL;
static _Atomic int ring_lock = 0;
static uint64_t last_ns = 0;
static char *script_path = NULL;
static PyObject *write_func = NULL;
static PyObject *script_obj = NULL;
static uint64_t start_ns = 0;
static _PyFrameEvalFunction prev_eval = NULL;
static char **filters = NULL;
static size_t filter_count = 0;

static void free_filters(void) {
    if (!filters)
        return;
    for (size_t i = 0; i < filter_count; i++)
        free(filters[i]);
    free(filters);
    filters = NULL;
    filter_count = 0;
}

static int load_filters(void) {
    const char *env = getenv("NYTPROF_FILTER");
    if (!env || !*env)
        return 0;
    char *copy = strdup(env);
    if (!copy)
        return -1;
    size_t alloc = 8;
    filters = calloc(alloc, sizeof(char *));
    if (!filters) {
        free(copy);
        return -1;
    }
    char *save = NULL;
    char *tok = strtok_r(copy, ",", &save);
    while (tok) {
        if (filter_count >= alloc) {
            alloc *= 2;
            char **tmp = realloc(filters, alloc * sizeof(char *));
            if (!tmp) {
                free(copy);
                free_filters();
                return -1;
            }
            filters = tmp;
        }
        filters[filter_count] = strdup(tok);
        if (!filters[filter_count]) {
            free(copy);
            free_filters();
            return -1;
        }
        filter_count++;
        tok = strtok_r(NULL, ",", &save);
    }
    free(copy);
    return 0;
}

/* spinlock helpers */
static inline void lock(void) {
    while (atomic_exchange_explicit(&ring_lock, 1, memory_order_acquire)) {
    }
}

static inline void unlock(void) {
    atomic_store_explicit(&ring_lock, 0, memory_order_release);
}

/* add line timing to ring */
static void record_line(int line, uint64_t dt) {
    size_t idx = (size_t)line & (RING_SIZE - 1);
    for (size_t i = 0; i < RING_SIZE; i++) {
        Rec *r = &ring[idx];
        if (r->line == 0 || r->line == (uint32_t)line) {
            if (r->line == 0)
                r->line = (uint32_t)line;
            r->calls += 1;
            r->inc_ns += dt;
            r->exc_ns += dt;
            return;
        }
        idx = (idx + 1) & (RING_SIZE - 1);
    }
}

/* trace callback */
static int tracefunc(PyObject *obj, PyFrameObject *f, int what, PyObject *arg) {
    if (what != PyTrace_LINE)
        return 0;
    if (filter_count) {
        PyObject *fsobj = PyOS_FSPath(f->f_code->co_filename);
        if (!fsobj) {
            PyErr_Clear();
            return 0;
        }
        const char *raw = PyUnicode_AsUTF8(fsobj);
        if (!raw) {
            PyErr_Clear();
            Py_DECREF(fsobj);
            return 0;
        }
#ifdef _WIN32
        char tmp[MAX_PATH];
        const char *full = _fullpath(tmp, raw, MAX_PATH) ? tmp : raw;
#else
        char tmp[PATH_MAX];
        const char *full = realpath(raw, tmp) ? tmp : raw;
#endif
        int matched = 0;
        for (size_t i = 0; i < filter_count; i++) {
#ifdef _WIN32
            if (PathMatchSpecA(full, filters[i])) {
                matched = 1;
                break;
            }
#else
            if (fnmatch(filters[i], full, 0) == 0) {
                matched = 1;
                break;
            }
#endif
        }
        Py_DECREF(fsobj);
        if (!matched)
            return 0;
    }
    int line = PyFrame_GetLineNumber(f);
    uint64_t now = PyTime_GetPerfCounter();
    uint64_t dt = last_ns ? now - last_ns : 0;
    last_ns = now;
    lock();
    record_line(line, dt);
    unlock();
    return 0;
}

/* eval frame wrapper */
static PyObject *tracer_eval(PyThreadState *ts, PyFrameObject *f, int throwflag) {
    Py_tracefunc oldfunc = ts->c_tracefunc;
    PyObject *oldobj = ts->c_traceobj;
    int olduse = ts->use_tracing;
    ts->c_tracefunc = tracefunc;
    ts->c_traceobj = NULL;
    ts->use_tracing = 1;
    PyObject *res = prev_eval(ts, f, throwflag);
    ts->c_tracefunc = oldfunc;
    ts->c_traceobj = oldobj;
    ts->use_tracing = olduse;
    return res;
}

/* shutdown handler */
static void tracer_shutdown(void) {
    if (!ring)
        return;
    PyGILState_STATE g = PyGILState_Ensure();

    struct stat st;
    uint32_t size = 0, mtime = 0;
    if (script_path && stat(script_path, &st) == 0) {
        size = (uint32_t)st.st_size;
        mtime = (uint32_t)st.st_mtime;
    }

    PyObject *records = PyList_New(0);
    if (!records)
        goto done;
    for (size_t i = 0; i < RING_SIZE; i++) {
        Rec *r = &ring[i];
        if (!r->line || !r->calls)
            continue;
        PyObject *t = PyTuple_New(4);
        if (!t)
            goto done;
        PyTuple_SET_ITEM(t, 0, PyLong_FromUnsignedLong(r->line));
        PyTuple_SET_ITEM(t, 1, PyLong_FromUnsignedLong(r->calls));
        PyTuple_SET_ITEM(t, 2, PyLong_FromUnsignedLongLong(r->inc_ns));
        PyTuple_SET_ITEM(t, 3, PyLong_FromUnsignedLongLong(r->exc_ns));
        PyList_Append(records, t);
        Py_DECREF(t);
    }

    if (write_func) {
        PyObject *path = PyUnicode_FromString("nytprof.out");
        PyObject *size_obj = PyLong_FromUnsignedLong(size);
        PyObject *mtime_obj = PyLong_FromUnsignedLong(mtime);
        PyObject *start_obj = PyLong_FromUnsignedLongLong(start_ns);
        PyObject *ticks_obj = PyLong_FromUnsignedLongLong(TICKS_PER_SEC);
        PyObject *args = PyTuple_Pack(7, path, script_obj, size_obj, mtime_obj,
                                     start_obj, ticks_obj, records);
        if (args) {
            PyObject *res = PyObject_CallObject(write_func, args);
            Py_XDECREF(res);
            Py_DECREF(args);
        }
        Py_DECREF(path);
        Py_DECREF(size_obj);
        Py_DECREF(mtime_obj);
        Py_DECREF(start_obj);
        Py_DECREF(ticks_obj);
    }
    Py_DECREF(records);

done:
    PyMem_RawFree(ring);
    ring = NULL;
    Py_XDECREF(write_func);
    Py_XDECREF(script_obj);
    free(script_path);
    free_filters();
    PyGILState_Release(g);
}

/* enable tracing */
static PyObject *ctrace_enable(PyObject *self, PyObject *args) {
    const char *path;
    unsigned long long start;
    if (!PyArg_ParseTuple(args, "sK", &path, &start))
        return NULL;
    if (ring)
        Py_RETURN_NONE;
    ring = PyMem_RawCalloc(RING_SIZE, sizeof(Rec));
    if (!ring)
        return PyErr_NoMemory();
    if (load_filters() < 0) {
        PyMem_RawFree(ring);
        ring = NULL;
        return PyErr_NoMemory();
    }
    start_ns = start;
    script_path = strdup(path);
    if (!script_path)
        return PyErr_NoMemory();
    script_obj = PyUnicode_FromString(path);
    if (!script_obj)
        return NULL;
    PyObject *mod = PyImport_ImportModule("pynytprof._cwrite");
    if (!mod)
        return NULL;
    write_func = PyObject_GetAttrString(mod, "write");
    Py_DECREF(mod);
    if (!write_func)
        return NULL;
    PyInterpreterState *interp = PyInterpreterState_Get();
    prev_eval = PyInterpreterState_GetEvalFrameFunc(interp);
    PyInterpreterState_SetEvalFrameFunc(interp, tracer_eval);
    Py_AtExit(tracer_shutdown);
    Py_RETURN_NONE;
}

static PyMethodDef Methods[] = {
    {"enable", ctrace_enable, METH_VARARGS, "enable c tracer"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moddef = {
    PyModuleDef_HEAD_INIT, "_tracer", NULL, -1, Methods
};

PyMODINIT_FUNC PyInit__tracer(void) { return PyModule_Create(&moddef); }
