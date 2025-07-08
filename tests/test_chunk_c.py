def test_c_writer_chunks(tmp_path):
    import subprocess, sys, os
    out = tmp_path/'c.out'
    subprocess.check_call([
        sys.executable,'-m','pynytprof.tracer',
        '-o',str(out),'-e','pass'
    ], env={**os.environ,'PYNYTPROF_WRITER':'c'})
    data = out.read_bytes()
    assert data.startswith(b'NYTProf 5 0\n')
    assert data.endswith(b'E\x00\x00\x00\x00')

