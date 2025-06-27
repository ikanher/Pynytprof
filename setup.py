from setuptools import setup, Extension
setup(
    name='pynytprof',
    version='0.0.0',
    packages=['pynytprof'],
    package_dir={'': 'src'},
    ext_modules=[
        Extension('pynytprof._writer', ['src/pynytprof/_writer.c']),
        Extension('pynytprof._tracer', ['src/pynytprof/_tracer.c']),
    ],
    entry_points={'console_scripts': ['pynytprof=pynytprof.__main__:cli']},
)
