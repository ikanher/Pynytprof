import io, struct
from pynytprof._pywrite import Writer

def test_p_chunk_is_21_bytes():
    buf = io.BytesIO()
    w = Writer(fp=buf)
    w._write_raw_P()
    data = buf.getvalue()
    assert data[:1] == b'P'
    assert len(data) == 21, (
        f'P record should be 21 bytes (tag+len+payload), got {len(data)}'
    )

