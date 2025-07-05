from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import warnings


class OptionalBuildExt(build_ext):
    """Allow failing optional extensions."""

    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception as exc:  # pragma: no cover - compile env may vary
            if ext.name == "pynytprof._cwrite":
                warnings.warn(
                    "Building _cwrite failed; falling back to pure-Python mode",
                    RuntimeWarning,
                )
            else:
                raise


setup(
    name="pynytprof",
    version="0.0.0",
    packages=["pynytprof"],
    package_dir={"": "src"},
    package_data={"pynytprof": ["*.c"]},
    include_package_data=True,
    ext_modules=[
        Extension("pynytprof._cwrite", ["src/pynytprof/_writer.c"]),
        Extension("pynytprof._tracer", ["src/pynytprof/_tracer.c"]),
    ],
    cmdclass={"build_ext": OptionalBuildExt},
    entry_points={"console_scripts": ["pynytprof=pynytprof.__main__:cli"]},
)
