// Compile with: gcc -shared -fPIC -I$(python -c "import sysconfig, sys; print(sysconfig.get_paths()['include'])") _writer.c -o _writer.so
#include <Python.h>
#include <stdint.h>
#include <stdio.h>

static PyObject *pynytprof_write_stub(PyObject *self, PyObject *args) {
    const char *path;
    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;
    FILE *fp = fopen(path, "wb");
    if (!fp)
        return PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);
    fwrite("NYTPROF\0", 1, 8, fp);
    uint32_t v[2] = {5, 0};
    fwrite(v, sizeof v, 1, fp);
    fclose(fp);
    Py_RETURN_NONE;
}

static PyMethodDef Methods[] = {
    {"write_stub", pynytprof_write_stub, METH_VARARGS, "Write minimal file"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef moddef = {
    PyModuleDef_HEAD_INIT, "pynyt_writer", NULL, -1, Methods};

PyMODINIT_FUNC PyInit_pynyt_writer(void) { return PyModule_Create(&moddef); }
