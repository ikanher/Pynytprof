import io
import os
from pynytprof._pywrite import Writer
from pynytprof.encoding import encode_u32

def test_p_record_size_varies():
    buf = io.BytesIO()
    w = Writer(fp=buf)
    w._write_raw_P()
    data = buf.getvalue()
    assert data[:1] == b'P'
    expected = 1 + len(encode_u32(os.getpid())) + len(encode_u32(os.getppid())) + 8
    assert len(data) == expected, (
        f'P record should be {expected} bytes (tag+payload), got {len(data)}'
    )

