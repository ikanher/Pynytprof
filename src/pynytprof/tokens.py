"""Subset of NYTProf binary token constants used by Pynytprof."""

NYTP_TAG_NEW_FID = 0x01
NYTP_TAG_SRC_LINE = 0x02
NYTP_TAG_STRING = ord("'")
NYTP_TAG_STRING_UTF8 = ord('"')
NYTP_TAG_TIME_LINE = ord('+')
NYTP_TAG_PID_END = ord('p')

__all__ = [
    "NYTP_TAG_NEW_FID",
    "NYTP_TAG_SRC_LINE",
    "NYTP_TAG_STRING",
    "NYTP_TAG_STRING_UTF8",
    "NYTP_TAG_TIME_LINE",
    "NYTP_TAG_PID_END",
]
