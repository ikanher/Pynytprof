import os
import subprocess
from pathlib import Path


def test_help_shows_commands():
    res = subprocess.run(['pynytprof', '--help'], text=True, capture_output=True)
    assert res.returncode == 0
    assert 'profile' in res.stdout
    assert 'verify' in res.stdout
    assert 'html' in res.stdout
    assert 'speedscope' in res.stdout


def test_profile_verify(tmp_path):
    script = Path(__file__).with_name('example_script.py')
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    proc = subprocess.run(['pynytprof', 'profile', str(script)], cwd=tmp_path, env=env)
    assert proc.returncode == 0
    proc = subprocess.run(
        ['pynytprof', 'verify', 'nytprof.out', '-q'],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ''
    proc = subprocess.run(
        ['pynytprof', 'verify', 'nytprof.out'],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert '\u2713' in proc.stdout


def test_exit_code_passthrough(tmp_path):
    script = tmp_path / 'exitme.py'
    script.write_text('import sys; sys.exit(3)\n')
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    proc = subprocess.run(['pynytprof', 'profile', str(script)], cwd=tmp_path, env=env)
    assert proc.returncode == 3

