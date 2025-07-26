import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer
from pynytprof.reader import header_scan
from pynytprof.protocol import read_u32
from pynytprof.nytprof_tags import (
    NYTP_TAG_NEW_FID,
    NYTP_TAG_STRING,
    NYTP_TAG_STRING_UTF8,
)


def test_first_token_is_new_fid(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)) as w:
        w.start_profile()
        w.end_profile()
    data = out.read_bytes()
    _, _, off = header_scan(data)
    assert data[off] == NYTP_TAG_NEW_FID
    val, off = read_u32(data, off + 1)  # fid
    val, off = read_u32(data, off)  # eval_fid
    val, off = read_u32(data, off)  # eval_line
    val, off = read_u32(data, off)  # flags
    val, off = read_u32(data, off)  # size
    val, off = read_u32(data, off)  # mtime
    assert data[off] in {NYTP_TAG_STRING, NYTP_TAG_STRING_UTF8}
