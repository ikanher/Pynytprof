def get_chunk_start(data):
    cutoff = data.index(b"\nP") + 1
    return cutoff


def parse_chunks(data: bytes) -> dict:
    chunks = {}
    idx = 0
    while idx < len(data):
        tag = data[idx : idx + 1]
        if tag in b"PDSCE":
            if tag == b"P":
                length = 16
                if idx + 1 + length > len(data):
                    break
                payload = data[idx + 1 : idx + 1 + length]
                off = idx
                chunks[tag.decode()] = {
                    "offset": off,
                    "length": length,
                    "payload": payload,
                }
                idx += 1 + length
                continue
            length = int.from_bytes(data[idx + 1 : idx + 5], "little")
            if idx + 5 + length > len(data):
                idx += 1
                continue
            payload = data[idx + 5 : idx + 5 + length]
            off = idx
            chunks[tag.decode()] = {
                "offset": off,
                "length": length,
                "payload": payload,
            }
            idx += 5 + length
        else:
            idx += 1
    return chunks
