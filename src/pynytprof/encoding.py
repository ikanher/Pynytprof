def encode_u32(n: int) -> bytes:
    '''
    NYTProf varint for *unsigned* 32-bit.
    Mirrors NYTP::output_tag_u32() without the tag byte.
    '''
    assert 0 <= n <= 0xFFFFFFFF
    if n < 0x80:
        return bytes([n])
    if n < 0x4000:
        return bytes([(n >> 8) | 0x80, n & 0xFF])
    if n < 0x200000:
        return bytes([
            (n >> 16) | 0xC0,
            (n >> 8) & 0xFF,
            n & 0xFF,
        ])
    if n < 0x10000000:
        return bytes([
            (n >> 24) | 0xE0,
            (n >> 16) & 0xFF,
            (n >> 8) & 0xFF,
            n & 0xFF,
        ])
    return b'\xFF' + n.to_bytes(4, 'big')


def encode_i32(n: int) -> bytes:
    '''Two’s-complement pass-through used by NYTProf.'''
    return encode_u32(n & 0xFFFFFFFF)
