def encode_u32(n: int) -> bytes:
    '''
    NYTProf varint for *unsigned* 32-bit.
    Mirrors NYTP::output_tag_u32() without the tag byte.
    '''
    assert 0 <= n <= 0xFFFFFFFF
    if n < 0x80:
        return bytes([n])
    if n < 0x4000:
        return bytes([(n >> 7) | 0x80, n & 0x7F])
    if n < 0x200000:
        return bytes([
            (n >> 14) | 0xC0,
            ((n >> 7) & 0x7F) | 0x80,
            n & 0x7F,
        ])
    if n < 0x10000000:
        return bytes([
            (n >> 21) | 0xE0,
            ((n >> 14) & 0x7F) | 0x80,
            ((n >> 7) & 0x7F) | 0x80,
            n & 0x7F,
        ])
    return b'\xFF' + n.to_bytes(4, 'big')


def encode_i32(n: int) -> bytes:
    '''Two’s-complement pass-through used by NYTProf.'''
    return encode_u32(n & 0xFFFFFFFF)


def decode_u32(buf: bytes, off: int = 0) -> tuple[int, int]:
    """Decode a NYTProf varint starting at ``off``."""
    first = buf[off]
    off += 1
    if first < 0x80:
        return first, off
    if first == 0xFF:
        val = int.from_bytes(buf[off:off + 4], 'big')
        off += 4
        return val, off

    bytes_read = [first]
    byte = first
    while byte >= 0x80:
        byte = buf[off]
        off += 1
        bytes_read.append(byte)
        if byte < 0x80:
            break

    n = len(bytes_read)
    masks = {1: 0x7F, 2: 0x7F, 3: 0x3F, 4: 0x1F}
    val = bytes_read[0] & masks.get(n, 0x7F)
    for b in bytes_read[1:]:
        val = (val << 7) | (b & 0x7F)
    return val, off


def decode_i32(buf: bytes, off: int = 0) -> tuple[int, int]:
    u, off = decode_u32(buf, off)
    if u & 0x80000000:
        u = -((~u + 1) & 0xFFFFFFFF)
    return u, off
