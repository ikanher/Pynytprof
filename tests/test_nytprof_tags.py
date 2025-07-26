import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof import nytprof_tags

HEADER = Path('vendor/NYTProf_refs/NYTProf.h').read_text()

TAG_MAP = {
    'NEW_FID': nytprof_tags.NYTP_TAG_NEW_FID,
    'TIME_LINE': nytprof_tags.NYTP_TAG_TIME_LINE,
    'TIME_BLOCK': nytprof_tags.NYTP_TAG_TIME_BLOCK,
    'SUB_ENTRY': nytprof_tags.NYTP_TAG_SUB_ENTRY,
    'SUB_RETURN': nytprof_tags.NYTP_TAG_SUB_RETURN,
    'SUB_INFO': nytprof_tags.NYTP_TAG_SUB_INFO,
    'SUB_CALLERS': nytprof_tags.NYTP_TAG_SUB_CALLERS,
    'SRC_LINE': nytprof_tags.NYTP_TAG_SRC_LINE,
    'DISCOUNT': nytprof_tags.NYTP_TAG_DISCOUNT,
    'STRING': nytprof_tags.NYTP_TAG_STRING,
    'STRING_UTF8': nytprof_tags.NYTP_TAG_STRING_UTF8,
    'PID_END': nytprof_tags.NYTP_TAG_PID_END,
    'START_DEFLATE': nytprof_tags.NYTP_TAG_START_DEFLATE,
}

def test_constants_match_header():
    for name, val in TAG_MAP.items():
        m = re.search(rf"#define\s+NYTP_TAG_{name}\s+'([^']+)'", HEADER)
        assert m, f'missing {name}'
        raw = m.group(1)
        if name == 'STRING':
            char = "'"
        else:
            char = raw
        assert val == ord(char), name
