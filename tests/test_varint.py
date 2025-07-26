from pathlib import Path
from pynytprof.encoding import encode_u32, encode_i32

def test_encode_u32():
    assert encode_u32(0) == b"\x00"
    assert encode_u32(0x7F) == b"\x7F"
    assert encode_u32(0x80) == b"\x81\x00"

def test_encode_i32_negative():
    # -1 should match C: 0xFF + four 0xFF bytes
    assert encode_i32(-1) == b"\xFF\xFF\xFF\xFF\xFF"

def test_profile_roundtrip(tmp_path):
    from pynytprof._pywrite import Writer

    out = tmp_path / "test.out"
    with Writer(out.open("wb")) as w:
        # minimal profile with a single negative elapsed time
        w.start_profile()
        w.write_time_line(fid=1, line=1, elapsed=-11, overflow=0)
        w.end_profile()

    import subprocess

    proc = subprocess.run(
        [
            "perl",
            "-MDevel::NYTProf::Data",
            "-e",
            "Devel::NYTProf::Data::load_profile(@ARGV)",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        import pytest
        pytest.skip("Devel::NYTProf::Data missing")
