import mmap
import struct
import zlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pynytprof.writer import Writer


def test_callgraph_chunk(tmp_path):
    out = tmp_path / "out.nyt"
    with Writer(str(out)) as w:
        fid = w.add_file(str(out), True)
        caller = w.sub_table.add(fid, 1, 2, "caller", "pkg")
        callee = w.sub_table.add(fid, 3, 4, "callee", "pkg")
        for _ in range(3):
            w.callgraph.add(caller, callee, 10)
    with out.open("rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        hdr_end = 0
        for _ in range(10):
            hdr_end = mm.find(b"\n", hdr_end) + 1
        off = hdr_end
        found = False
        while off < mm.size():
            tag = mm[off : off + 1]
            length = struct.unpack_from("<I", mm, off + 1)[0]
            off += 5
            payload = mm[off : off + length]
            off += length
            if tag == b"C":
                payload = zlib.decompress(payload)
                vals = struct.unpack_from("<IIIQQ", payload, 0)
                assert vals[:3] == (caller, callee, 3)
                found = True
                break
        mm.close()
    assert found
    # header is not rewritten with callgraph statistics
