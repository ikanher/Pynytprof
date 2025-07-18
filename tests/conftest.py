import re


def get_chunk_start(data):
    idx = data.index(b"\nP") + 1
    assert data[idx:idx + 1] == b"P"
    return idx


def parse_chunks(data: bytes) -> dict:
    chunks = {}
    try:
        idx = data.index(b"\nP") + 1
    except ValueError:
        idx = 0
    while idx < len(data):
        tag = data[idx : idx + 1]
        if tag in b"PDSCEF":
            if tag == b"P":
                if idx + 17 > len(data):
                    break
                payload = data[idx + 1 : idx + 17]
                off = idx
                chunks[tag.decode()] = {
                    "offset": off,
                    "length": 16,
                    "payload": payload,
                }
                idx += 17
                continue
            if tag == b"E":
                off = idx
                chunks[tag.decode()] = {"offset": off, "length": 0, "payload": b""}
                idx += 1
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
