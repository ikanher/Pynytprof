def get_chunk_start(data):
    cutoff = data.index(b"\nP") + 1
    return cutoff
