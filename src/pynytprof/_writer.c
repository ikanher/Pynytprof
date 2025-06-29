#include <Python.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void dbg_chunk(char tok, uint32_t len) {
    if (getenv("PYNTP_DEBUG"))
        fprintf(stderr, "[DBG] write chunk %c len=%u\n", tok, len);
}

static void put_u32le(unsigned char *p, uint32_t v) {
    p[0] = (unsigned char)(v & 0xFF);
    p[1] = (unsigned char)((v >> 8) & 0xFF);
    p[2] = (unsigned char)((v >> 16) & 0xFF);
    p[3] = (unsigned char)((v >> 24) & 0xFF);
}

static void put_u64le(unsigned char *p, uint64_t v) {
    put_u32le(p, (uint32_t)v);
    put_u32le(p + 4, (uint32_t)(v >> 32));
}

static void write_header(FILE *fp) {
    static const unsigned char HDR[16] =
        "NYTPROF\0" "\x05\0\0\0" "\0\0\0\0";
    fwrite(HDR, 1, 16, fp);
}

static void write_H_chunk(FILE *fp) {
    static const unsigned char H[13] =
        "H" /* token */
        "\x08\x00\x00\x00" /* u32 length = 8 */
        "\x05\x00\x00\x00" /* u32 major = 5 */
        "\x00\x00\x00\x00"; /* u32 minor = 0 */
    dbg_chunk('H', 8);
    fwrite(H, 1, sizeof H, fp);
}

static PyObject *pynytprof_write(PyObject *self, PyObject *args) {
    PyObject *path_obj, *files_obj, *defs_obj, *calls_obj, *lines_obj, *start_obj,
        *ticks_obj;
    if (!PyArg_ParseTuple(args, "OOOOOOO", &path_obj, &files_obj, &defs_obj,
                          &calls_obj, &lines_obj, &start_obj, &ticks_obj))
        return NULL;

    const char *path = PyUnicode_AsUTF8(path_obj);
    if (!path)
        return NULL;

    uint64_t start_ns = PyLong_AsUnsignedLongLong(start_obj);
    uint64_t ticks_per_sec = PyLong_AsUnsignedLongLong(ticks_obj);
    if (PyErr_Occurred())
        return NULL;

    PyObject *files = PySequence_Fast(files_obj, "files");
    PyObject *defs = PySequence_Fast(defs_obj, "defs");
    PyObject *calls = PySequence_Fast(calls_obj, "calls");
    PyObject *lines = PySequence_Fast(lines_obj, "lines");
    if (!files || !defs || !calls || !lines)
        return NULL;

    Py_ssize_t nfiles = PySequence_Fast_GET_SIZE(files);
    Py_ssize_t ndefs = PySequence_Fast_GET_SIZE(defs);
    Py_ssize_t ncalls = PySequence_Fast_GET_SIZE(calls);
    Py_ssize_t nlines = PySequence_Fast_GET_SIZE(lines);

    FILE *fp = fopen(path, "wb");
    if (!fp)
        return PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);

    write_header(fp);
    write_H_chunk(fp);

    char abuf[128];
    int apos = 0;
    apos += sprintf(abuf + apos, "ticks_per_sec=%llu",
                    (unsigned long long)ticks_per_sec);
    abuf[apos++] = '\0';
    apos += sprintf(abuf + apos, "start_time=%llu",
                    (unsigned long long)start_ns);
    abuf[apos++] = '\0';
    size_t a_len = (size_t)apos;

    char *achunk = malloc(5 + a_len);
    if (!achunk)
        goto mem_err;
    achunk[0] = 'A';
    put_u32le((unsigned char *)achunk + 1, (uint32_t)a_len);
    memcpy(achunk + 5, abuf, a_len);

    /* F chunk */
    size_t f_len = 0;
    for (Py_ssize_t i = 0; i < nfiles; i++) {
        PyObject *it = PySequence_Fast_GET_ITEM(files, i);
        const char *pstr = PyUnicode_AsUTF8(PyTuple_GET_ITEM(it, 4));
        f_len += 16 + strlen(pstr) + 1;
    }
    char *fchunk = malloc(5 + f_len);
    if (!fchunk) {
        free(achunk);
        goto mem_err;
    }
    fchunk[0] = 'F';
    put_u32le((unsigned char *)fchunk + 1, (uint32_t)f_len);
    unsigned char *p = (unsigned char *)fchunk + 5;
    for (Py_ssize_t i = 0; i < nfiles; i++) {
        PyObject *it = PySequence_Fast_GET_ITEM(files, i);
        uint32_t fid = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 0));
        uint32_t flags = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 1));
        uint32_t size = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 2));
        uint32_t mt = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 3));
        const char *pstr = PyUnicode_AsUTF8(PyTuple_GET_ITEM(it, 4));
        size_t l = strlen(pstr);
        put_u32le(p, fid);
        p += 4;
        put_u32le(p, flags);
        p += 4;
        put_u32le(p, size);
        p += 4;
        put_u32le(p, mt);
        p += 4;
        memcpy(p, pstr, l);
        p[l] = 0;
        p += l + 1;
    }

    /* D chunk */
    size_t d_len = 0;
    for (Py_ssize_t i = 0; i < ndefs; i++) {
        PyObject *it = PySequence_Fast_GET_ITEM(defs, i);
        const char *name = PyUnicode_AsUTF8(PyTuple_GET_ITEM(it, 4));
        d_len += 16 + strlen(name) + 1;
    }
    char *dchunk = malloc(5 + d_len);
    if (!dchunk) {
        free(achunk);
        free(fchunk);
        goto mem_err;
    }
    dchunk[0] = 'D';
    put_u32le((unsigned char *)dchunk + 1, (uint32_t)d_len);
    p = (unsigned char *)dchunk + 5;
    for (Py_ssize_t i = 0; i < ndefs; i++) {
        PyObject *it = PySequence_Fast_GET_ITEM(defs, i);
        uint32_t sid = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 0));
        uint32_t fid = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 1));
        uint32_t sl = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 2));
        uint32_t el = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 3));
        const char *name = PyUnicode_AsUTF8(PyTuple_GET_ITEM(it, 4));
        size_t l = strlen(name);
        put_u32le(p, sid);
        p += 4;
        put_u32le(p, fid);
        p += 4;
        put_u32le(p, sl);
        p += 4;
        put_u32le(p, el);
        p += 4;
        memcpy(p, name, l);
        p[l] = 0;
        p += l + 1;
    }

    /* C chunk */
    size_t c_len = (size_t)ncalls * 28;
    char *cchunk = malloc(5 + c_len);
    if (!cchunk) {
        free(achunk);
        free(fchunk);
        free(dchunk);
        goto mem_err;
    }
    cchunk[0] = 'C';
    put_u32le((unsigned char *)cchunk + 1, (uint32_t)c_len);
    p = (unsigned char *)cchunk + 5;
    for (Py_ssize_t i = 0; i < ncalls; i++) {
        PyObject *it = PySequence_Fast_GET_ITEM(calls, i);
        uint32_t fid = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 0));
        uint32_t line = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 1));
        uint32_t sid = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 2));
        uint64_t inc = PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(it, 3));
        uint64_t exc = PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(it, 4));
        inc /= 100;
        exc /= 100;
        put_u32le(p, fid);
        p += 4;
        put_u32le(p, line);
        p += 4;
        put_u32le(p, sid);
        p += 4;
        put_u64le(p, inc);
        p += 8;
        put_u64le(p, exc);
        p += 8;
    }

    /* S chunk */
    size_t s_len = (size_t)nlines * 28;
    char *schunk = malloc(5 + s_len);
    if (!schunk) {
        free(achunk);
        free(fchunk);
        free(dchunk);
        free(cchunk);
        goto mem_err;
    }
    schunk[0] = 'S';
    put_u32le((unsigned char *)schunk + 1, (uint32_t)s_len);
    p = (unsigned char *)schunk + 5;
    for (Py_ssize_t i = 0; i < nlines; i++) {
        PyObject *it = PySequence_Fast_GET_ITEM(lines, i);
        uint32_t fid = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 0));
        uint32_t line = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 1));
        uint32_t calls_v = (uint32_t)PyLong_AsUnsignedLong(PyTuple_GET_ITEM(it, 2));
        uint64_t inc = PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(it, 3));
        uint64_t exc = PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(it, 4));
        inc /= 100;
        exc /= 100;
        put_u32le(p, fid);
        p += 4;
        put_u32le(p, line);
        p += 4;
        put_u32le(p, calls_v);
        p += 4;
        put_u64le(p, inc);
        p += 8;
        put_u64le(p, exc);
        p += 8;
    }

    unsigned char echunk[5];
    echunk[0] = 'E';
    put_u32le(echunk + 1, 0);

    dbg_chunk('A', (uint32_t)a_len);
    fwrite(achunk, 5 + a_len, 1, fp);
    dbg_chunk('F', (uint32_t)f_len);
    fwrite(fchunk, 5 + f_len, 1, fp);
    dbg_chunk('D', (uint32_t)d_len);
    fwrite(dchunk, 5 + d_len, 1, fp);
    dbg_chunk('C', (uint32_t)c_len);
    fwrite(cchunk, 5 + c_len, 1, fp);
    dbg_chunk('S', (uint32_t)s_len);
    fwrite(schunk, 5 + s_len, 1, fp);
    dbg_chunk('E', 0);
    fwrite(echunk, 5, 1, fp);

    free(achunk);
    free(fchunk);
    free(dchunk);
    free(cchunk);
    free(schunk);
    fclose(fp);
    Py_RETURN_NONE;

mem_err:
    fclose(fp);
    return PyErr_NoMemory();
}

static PyMethodDef Methods[] = {{"write", pynytprof_write, METH_VARARGS, "write"},
                                {NULL, NULL, 0, NULL}};

static struct PyModuleDef moddef = {PyModuleDef_HEAD_INIT, "_cwrite", NULL,
                                    -1, Methods};

PyMODINIT_FUNC PyInit__cwrite(void) { return PyModule_Create(&moddef); }
