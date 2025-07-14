def get_chunk_start(data):
    cutoff = data.index(b"\nP") + 1
    return cutoff


def parse_chunks(data: bytes) -> dict:
    chunks = {}
    idx = 0
    while idx + 5 <= len(data):
        tag = data[idx : idx + 1]
        if tag in b"PDSCE":
            length = int.from_bytes(data[idx + 1 : idx + 5], "little")
            if idx + 5 + length > len(data):
                idx += 1
                continue
            payload = data[idx + 5 : idx + 5 + length]
            off = idx - 1 if idx > 0 and data[idx - 1:idx] == b"\n" else idx
            chunks[tag.decode()] = {
                "offset": off,
                "length": length,
                "payload": payload,
            }
            idx += 5 + length
        else:
            idx += 1
    return chunks
