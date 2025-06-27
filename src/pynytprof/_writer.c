#include <Python.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

static PyObject *pynytprof_write(PyObject *self, PyObject *args) {
    PyObject *path_obj, *script_obj, *size_obj, *mtime_obj,
        *start_obj, *ticks_obj, *records_obj;
    if (!PyArg_ParseTuple(args, "OOOOOOO", &path_obj, &script_obj, &size_obj,
                          &mtime_obj, &start_obj, &ticks_obj, &records_obj))
        return NULL;

    const char *path = PyUnicode_AsUTF8(path_obj);
    const char *script = PyUnicode_AsUTF8(script_obj);
    if (!path || !script)
        return NULL;

    uint32_t size = (uint32_t)PyLong_AsUnsignedLongLong(size_obj);
    uint32_t mtime = (uint32_t)PyLong_AsUnsignedLongLong(mtime_obj);
    uint64_t start_ns = PyLong_AsUnsignedLongLong(start_obj);
    uint64_t ticks_per_sec = PyLong_AsUnsignedLongLong(ticks_obj);
    if (PyErr_Occurred())
        return NULL;

    PyObject *seq = PySequence_Fast(records_obj, "records must be a sequence");
    if (!seq)
        return NULL;
    Py_ssize_t nrec = PySequence_Fast_GET_SIZE(seq);

    FILE *fp = fopen(path, "wb");
    if (!fp) {
        Py_DECREF(seq);
        return PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);
    }

    unsigned char header[16];
    memcpy(header, "NYTPROF\0", 8);
    put_u32le(header + 8, 5);
    put_u32le(header + 12, 0);

    if (nrec == 0) {
        unsigned char buf[21];
        memcpy(buf, header, 16);
        buf[16] = 'E';
        put_u32le(buf + 17, 0);
        fwrite(buf, 21, 1, fp);
        fclose(fp);
        Py_DECREF(seq);
        Py_RETURN_NONE;
    }

    unsigned char hchunk[13];
    hchunk[0] = 'H';
    put_u32le(hchunk + 1, 8);
    put_u32le(hchunk + 5, 5);
    put_u32le(hchunk + 9, 0);

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

    size_t script_len = strlen(script);
    size_t f_len = 16 + script_len + 1;
    char *fchunk = malloc(5 + f_len);
    if (!fchunk) {
        free(achunk);
        goto mem_err;
    }
    fchunk[0] = 'F';
    put_u32le((unsigned char *)fchunk + 1, (uint32_t)f_len);
    unsigned char *p = (unsigned char *)fchunk + 5;
    put_u32le(p, 0);
    p += 4;
    put_u32le(p, 0x10);
    p += 4;
    put_u32le(p, size);
    p += 4;
    put_u32le(p, mtime);
    p += 4;
    memcpy(p, script, script_len);
    p[script_len] = 0;

    size_t s_len = (size_t)nrec * 28;
    char *schunk = malloc(5 + s_len);
    if (!schunk) {
        free(achunk);
        free(fchunk);
        goto mem_err;
    }
    schunk[0] = 'S';
    put_u32le((unsigned char *)schunk + 1, (uint32_t)s_len);
    p = (unsigned char *)schunk + 5;
    for (Py_ssize_t i = 0; i < nrec; i++) {
        PyObject *item = PySequence_Fast_GET_ITEM(seq, i);
        if (!PyTuple_Check(item) || PyTuple_GET_SIZE(item) != 4) {
            free(achunk);
            free(fchunk);
            free(schunk);
            Py_DECREF(seq);
            fclose(fp);
            PyErr_SetString(PyExc_TypeError, "record tuple");
            return NULL;
        }
        uint32_t line = (uint32_t)PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(item, 0));
        uint32_t calls = (uint32_t)PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(item, 1));
        uint64_t inc = PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(item, 2));
        uint64_t exc = PyLong_AsUnsignedLongLong(PyTuple_GET_ITEM(item, 3));
        if (PyErr_Occurred()) {
            free(achunk);
            free(fchunk);
            free(schunk);
            Py_DECREF(seq);
            fclose(fp);
            return NULL;
        }
        inc /= 100;
        exc /= 100;
        put_u32le(p, 0);
        p += 4;
        put_u32le(p, line);
        p += 4;
        put_u32le(p, calls);
        p += 4;
        put_u64le(p, inc);
        p += 8;
        put_u64le(p, exc);
        p += 8;
    }

    unsigned char echunk[5];
    echunk[0] = 'E';
    put_u32le(echunk + 1, 0);

    fwrite(header, 16, 1, fp);
    fwrite(hchunk, 13, 1, fp);
    fwrite(achunk, 5 + a_len, 1, fp);
    fwrite(fchunk, 5 + f_len, 1, fp);
    fwrite(schunk, 5 + s_len, 1, fp);
    fwrite(echunk, 5, 1, fp);

    free(achunk);
    free(fchunk);
    free(schunk);
    fclose(fp);
    Py_DECREF(seq);
    Py_RETURN_NONE;

mem_err:
    fclose(fp);
    Py_DECREF(seq);
    return PyErr_NoMemory();
}

static PyMethodDef Methods[] = {{"write", pynytprof_write, METH_VARARGS, "write"},
                                {NULL, NULL, 0, NULL}};

static struct PyModuleDef moddef = {PyModuleDef_HEAD_INIT, "_cwrite", NULL,
                                    -1, Methods};

PyMODINIT_FUNC PyInit__cwrite(void) { return PyModule_Create(&moddef); }
