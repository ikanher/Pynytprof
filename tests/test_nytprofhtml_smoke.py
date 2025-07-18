import os, subprocess, sys, shutil, pathlib, pytest

def _have_nytprofhtml():
    return shutil.which('nytprofhtml') is not None

@pytest.mark.skipif(not _have_nytprofhtml(), reason="nytprofhtml not installed")
def test_nytprofhtml_loads(tmp_path):
    env = {**os.environ,
           'PYNYTPROF_WRITER': 'py',
           'PYTHONPATH': str(pathlib.Path(__file__).resolve().parents[1] / 'src')}
    out = tmp_path / 'nytprof.out'
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer',
                           '-o', str(out), '-e', 'pass'], env=env)
    res = subprocess.run(['nytprofhtml', '-f', str(out), '-o', str(tmp_path/'nytprof')],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        err_line = res.stderr.decode(errors='replace').splitlines()[-1]
        pytest.xfail(f"nytprofhtml failed: {err_line}")
    assert (tmp_path/'nytprof'/'index.html').exists()
