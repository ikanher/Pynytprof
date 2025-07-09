def get_chunk_start(data):
    cutoff = data.index(b"\n\n") + 2
    return cutoff
