from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import warnings
import sys
import os
from pathlib import Path
import subprocess
import time

build_tag = os.environ.get("PYNYTPROF_BUILD_TAG")
if not build_tag:
    # try git commit, fall back to timestamp
    try:
        build_tag = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
        )
    except Exception:
        build_tag = str(int(time.time()))

Path("src/pynytprof/_build_tag.py").write_text(f'__pynytprof_build__ = "{build_tag}"\n')


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
        define_macros=[
            ("PY_SSIZE_T_CLEAN", None),
            ("PYNYTPROF_BUILD_TAG", f'"{build_tag}"'),
        ],
    ),
    Extension(
        "pynytprof._ctrace",
        ["src/pynytprof/_ctrace.c"],
        optional=True,
        define_macros=[
            ("PY_SSIZE_T_CLEAN", None),
            ("PYNYTPROF_BUILD_TAG", f'"{build_tag}"'),
        ],
    ),
]

if sys.version_info >= (3, 12):
    # Only skip _ctrace; keep _cwrite for binary output support
    extensions = [e for e in extensions if e.name != "pynytprof._ctrace"]

setup(
    name="pynytprof",
    use_scm_version={"write_to": "src/pynytprof/_version.py"},
    packages=["pynytprof"],
    package_dir={"": "src"},
    package_data={"pynytprof": ["*.c"]},
    include_package_data=True,
    ext_modules=extensions,
    cmdclass={"build_ext": OptionalBuildExt},
    entry_points={"console_scripts": ["pynytprof=pynytprof.cli:main"]},
)
