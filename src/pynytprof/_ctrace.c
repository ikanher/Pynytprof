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
    PyObject *path;
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
static uint64_t start_ns = 0;
static _PyFrameEvalFunction prev_eval = NULL;
static char **filters = NULL;
static size_t filter_count = 0;
static PyObject *code_to_id = NULL;
static PyObject *defs_list = NULL;
static PyObject *calls_list = NULL;

#define MAX_STACK 1024
typedef struct {
    PyObject *path;
    uint32_t line;
    uint32_t sub_id;
    uint64_t start_ns;
    uint64_t child_ns;
} StackItem;
static StackItem stack[MAX_STACK];
static int stack_top = 0;
static uint32_t next_sub_id = 1;

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
static void record_line(PyObject *path, int line, uint64_t dt) {
    size_t idx = ((size_t)line ^ (size_t)path) & (RING_SIZE - 1);
    for (size_t i = 0; i < RING_SIZE; i++) {
        Rec *r = &ring[idx];
        if (r->path == NULL) {
            r->path = path;
            Py_INCREF(path);
            r->line = (uint32_t)line;
            r->calls = 1;
            r->inc_ns += dt;
            r->exc_ns += dt;
            return;
        }
        if (r->line == (uint32_t)line && r->path == path) {
            r->calls += 1;
            r->inc_ns += dt;
            r->exc_ns += dt;
            return;
        }
        idx = (idx + 1) & (RING_SIZE - 1);
    }
}

/* map code objects to sub IDs and record definitions */
static uint32_t get_sub_id(PyCodeObject *code) {
    PyObject *id_obj = PyDict_GetItem(code_to_id, (PyObject *)code);
    if (id_obj)
        return (uint32_t)PyLong_AsUnsignedLong(id_obj);

    uint32_t sub_id = next_sub_id++;
    id_obj = PyLong_FromUnsignedLong(sub_id);
    PyDict_SetItem(code_to_id, (PyObject *)code, id_obj);
    Py_DECREF(id_obj);

    PyObject *name = code->co_name;
    if (PyUnicode_Check(name) && PyUnicode_CompareWithASCIIString(name, "<module>") == 0)
        name = PyUnicode_FromString("(module)");
    else
        Py_INCREF(name);

    PyObject *def = PyTuple_New(5);
    PyTuple_SET_ITEM(def, 0, PyLong_FromUnsignedLong(sub_id));
    Py_INCREF(code->co_filename);
    PyTuple_SET_ITEM(def, 1, code->co_filename);
    PyTuple_SET_ITEM(def, 2, PyLong_FromLong(code->co_firstlineno));
    PyTuple_SET_ITEM(def, 3, PyLong_FromLong(code->co_firstlineno));
    PyTuple_SET_ITEM(def, 4, name);
    PyList_Append(defs_list, def);
    Py_DECREF(def);

    return sub_id;
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
    record_line(f->f_code->co_filename, line, dt);
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

    PyObject *call_path = NULL;
    uint32_t call_line = 0;
    if (f->f_back) {
        call_path = f->f_back->f_code->co_filename;
        Py_INCREF(call_path);
        call_line = (uint32_t)PyFrame_GetLineNumber(f->f_back);
    }

    uint32_t sub_id = get_sub_id((PyCodeObject *)f->f_code);
    uint64_t start = PyTime_GetPerfCounter();
    if (stack_top < MAX_STACK) {
        stack[stack_top].path = call_path;
        stack[stack_top].line = call_line;
        stack[stack_top].sub_id = sub_id;
        stack[stack_top].start_ns = start;
        stack[stack_top].child_ns = 0;
        stack_top++;
    } else {
        Py_XDECREF(call_path);
    }

    PyObject *res = prev_eval(ts, f, throwflag);
    uint64_t end = PyTime_GetPerfCounter();

    if (stack_top > 0) {
        StackItem item = stack[--stack_top];
        uint64_t dur = end - item.start_ns;
        uint64_t exc = dur - item.child_ns;
        PyObject *t = PyTuple_New(5);
        if (item.path)
            PyTuple_SET_ITEM(t, 0, item.path);
        else {
            Py_INCREF(Py_None);
            PyTuple_SET_ITEM(t, 0, Py_None);
        }
        PyTuple_SET_ITEM(t, 1, PyLong_FromUnsignedLong(item.line));
        PyTuple_SET_ITEM(t, 2, PyLong_FromUnsignedLong(item.sub_id));
        PyTuple_SET_ITEM(t, 3, PyLong_FromUnsignedLongLong(dur));
        PyTuple_SET_ITEM(t, 4, PyLong_FromUnsignedLongLong(exc));
        PyList_Append(calls_list, t);
        Py_DECREF(t);
        if (stack_top > 0)
            stack[stack_top - 1].child_ns += dur;
    }

    ts->c_tracefunc = oldfunc;
    ts->c_traceobj = oldobj;
    ts->use_tracing = olduse;
    return res;
}

/* shutdown handler */
/* dump collected data */
static PyObject *ctrace_dump(PyObject *self, PyObject *args) {
    PyObject *records = PyList_New(0);
    if (!records)
        return NULL;
    for (size_t i = 0; i < RING_SIZE; i++) {
        Rec *r = &ring[i];
        if (!r->path || !r->calls)
            continue;
        PyObject *t = PyTuple_New(5);
        PyTuple_SET_ITEM(t, 0, r->path); /* steal */
        PyTuple_SET_ITEM(t, 1, PyLong_FromUnsignedLong(r->line));
        PyTuple_SET_ITEM(t, 2, PyLong_FromUnsignedLong(r->calls));
        PyTuple_SET_ITEM(t, 3, PyLong_FromUnsignedLongLong(r->inc_ns));
        PyTuple_SET_ITEM(t, 4, PyLong_FromUnsignedLongLong(r->exc_ns));
        PyList_Append(records, t);
        Py_DECREF(t);
        r->path = NULL;
    }
    PyObject *defs = defs_list ? defs_list : PyList_New(0);
    PyObject *calls = calls_list ? calls_list : PyList_New(0);
    Py_INCREF(defs);
    Py_INCREF(calls);
    PyObject *ret = PyTuple_Pack(3, defs, calls, records);
    Py_DECREF(defs);
    Py_DECREF(calls);
    Py_DECREF(records);

    PyMem_RawFree(ring);
    ring = NULL;
    Py_CLEAR(defs_list);
    Py_CLEAR(calls_list);
    Py_CLEAR(code_to_id);
    free(script_path);
    script_path = NULL;
    free_filters();
    return ret;
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
    code_to_id = PyDict_New();
    defs_list = PyList_New(0);
    calls_list = PyList_New(0);
    if (!code_to_id || !defs_list || !calls_list)
        return PyErr_NoMemory();
    PyInterpreterState *interp = PyInterpreterState_Get();
    prev_eval = PyInterpreterState_GetEvalFrameFunc(interp);
    PyInterpreterState_SetEvalFrameFunc(interp, tracer_eval);
    Py_RETURN_NONE;
}

static PyMethodDef Methods[] = {
    {"enable", ctrace_enable, METH_VARARGS, "enable c tracer"},
    {"dump", ctrace_dump, METH_NOARGS, "dump collected data"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moddef = {
    PyModuleDef_HEAD_INIT, "_ctrace", NULL, -1, Methods
};

PyMODINIT_FUNC PyInit__ctrace(void) { return PyModule_Create(&moddef); }
