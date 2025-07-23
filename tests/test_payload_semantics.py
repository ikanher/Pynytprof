import struct

from tests.test_header_spec import profile_bytes


def parse_s(payload: bytes):
    off = 0
    st = struct.Struct('<IIIQQ')
    while off < len(payload):
        st.unpack_from(payload, off)
        off += st.size
    assert off == len(payload), f'S leftover {len(payload)-off}'


def parse_f(payload: bytes):
    off = 0
    st = struct.Struct('<II')
    while off < len(payload):
        st.unpack_from(payload, off)
        off += st.size
    assert off == len(payload), f'F leftover {len(payload)-off}'


def parse_d(payload: bytes):
    off = 0
    while off < len(payload):
        tok = payload[off]
        off += 1
        if tok == 0:
            break
        fid, line, dur = struct.unpack_from('<IIQ', payload, off)
        off += 16
    assert off == len(payload), f'D leftover {len(payload)-off}'


def parse_c(payload: bytes):
    off = 0
    st = struct.Struct('<IIIQQ')
    while off < len(payload):
        st.unpack_from(payload, off)
        off += st.size
    assert off == len(payload), f'C leftover {len(payload)-off}'


def test_payload_semantics(tmp_path):
    data = profile_bytes(tmp_path)
    off = data.index(b"\nP") + 1
    assert data[off] == ord("P")
    off += 17

    def get(tag):
        nonlocal off
        assert data[off] == ord(tag)
        ln = int.from_bytes(data[off+1:off+5], "little")
        payload = data[off+5:off+5+ln]
        off += 5 + ln
        return payload

    s = get('S'); parse_s(s)
    f = get('F'); parse_f(f)
    d = get('D'); parse_d(d)
    c = get('C'); parse_c(c)
    assert data[off] == ord('E')
    off += 1
    assert off == len(data)
