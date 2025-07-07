from pynytprof.writer import Writer


def test_text_header(tmp_path):
    out = tmp_path / "out.nyt"
    with Writer(str(out)):
        pass
    first = open(out, "rb").read().split(b"\n")[0]
    assert first == b"file=" + str(out).encode()
