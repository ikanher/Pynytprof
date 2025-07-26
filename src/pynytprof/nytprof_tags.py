# Minimal NYTProf tag constants derived from NYTProf headers

# Values taken from vendor/NYTProf_refs/FileHandle.h
NYTP_TAG_NEW_FID = ord('@')
NYTP_TAG_TIME_LINE = ord('+')
NYTP_TAG_TIME_BLOCK = ord('*')
NYTP_TAG_SUB_ENTRY = ord('>')
NYTP_TAG_SUB_RETURN = ord('<')
NYTP_TAG_SUB_INFO = ord('s')
NYTP_TAG_SUB_CALLERS = ord('c')
NYTP_TAG_SRC_LINE = ord('S')
NYTP_TAG_DISCOUNT = ord('-')
NYTP_TAG_STRING = ord("'")
NYTP_TAG_STRING_UTF8 = ord('"')
NYTP_TAG_PID_END = ord('p')
NYTP_TAG_START_DEFLATE = ord('z')

__all__ = [
    'NYTP_TAG_NEW_FID',
    'NYTP_TAG_TIME_LINE',
    'NYTP_TAG_TIME_BLOCK',
    'NYTP_TAG_SUB_ENTRY',
    'NYTP_TAG_SUB_RETURN',
    'NYTP_TAG_SUB_INFO',
    'NYTP_TAG_SUB_CALLERS',
    'NYTP_TAG_SRC_LINE',
    'NYTP_TAG_DISCOUNT',
    'NYTP_TAG_STRING',
    'NYTP_TAG_STRING_UTF8',
    'NYTP_TAG_PID_END',
    'NYTP_TAG_START_DEFLATE',
]
