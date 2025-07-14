import subprocess, sys, struct, os, tempfile, pathlib

def test_exactly_one_p_record(tmp_path):
    out = tmp_path/"nytprof.out"
    subprocess.check_call([sys.executable, "-m", "pynytprof.tracer",
                            "-o", str(out), "-e", "pass"],
                          env={**os.environ, "PYNYTPROF_WRITER":"py"})
    data = out.read_bytes()
    hdr = b'P' + (16).to_bytes(4, 'little')
    assert data.count(hdr) == 1, "duplicate P TLV detected"
    # ensure first S follows at banner_end + 21
    s_off = data.index(b'S')
    p_off = data.index(hdr)
    assert s_off == p_off + 21
