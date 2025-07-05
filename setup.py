from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import warnings
import sys


class OptionalBuildExt(build_ext):
    """Allow failing optional extensions."""

    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception as exc:  # pragma: no cover - compile env may vary
            warnings.warn(f"Skipping {ext.name}: {exc}", RuntimeWarning)
            ext._build_failed = True

    def copy_extensions_to_source(self):  # pragma: no cover - build env varies
        self.extensions = [e for e in self.extensions if not getattr(e, "_build_failed", False)]
        super().copy_extensions_to_source()


extensions = [
    Extension(
        "pynytprof._cwrite",
        ["src/pynytprof/_writer.c"],
        optional=True,
        define_macros=[("PY_SSIZE_T_CLEAN", None)],
    ),
    Extension(
        "pynytprof._ctrace",
        ["src/pynytprof/_ctrace.c"],
        optional=True,
        define_macros=[("PY_SSIZE_T_CLEAN", None)],
    ),
]

if sys.version_info >= (3, 12):
    extensions = [e for e in extensions if e.name != "pynytprof._ctrace"]

setup(
    name="pynytprof",
    version="0.0.0",
    packages=["pynytprof"],
    package_dir={"": "src"},
    package_data={"pynytprof": ["*.c"]},
    include_package_data=True,
    ext_modules=extensions,
    cmdclass={"build_ext": OptionalBuildExt},
    entry_points={"console_scripts": ["pynytprof=pynytprof.cli:main"]},
)
