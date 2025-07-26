"""NYTProf protocol tag constants (minimal subset)."""

# These values mirror those defined in NYTProf's XS sources.  We only
# expose the small subset that Pynytprof currently emits/consumes.

NYTP_TAG_NEW_FID = 0x01
NYTP_TAG_SRC_LINE = 0x02
NYTP_TAG_STRING = ord("'")
NYTP_TAG_STRING_UTF8 = ord('"')
NYTP_TAG_TIME_LINE = ord('+')
NYTP_TAG_PID_END = ord('p')

# Exported list of known tags for quick membership tests in the unit tests
# and debug helpers.  Keep the order stable.
KNOWN_TAGS = [
    NYTP_TAG_NEW_FID,
    NYTP_TAG_SRC_LINE,
    NYTP_TAG_STRING,
    NYTP_TAG_STRING_UTF8,
    NYTP_TAG_TIME_LINE,
    NYTP_TAG_PID_END,
]

__all__ = [
    "NYTP_TAG_NEW_FID",
    "NYTP_TAG_SRC_LINE",
    "NYTP_TAG_STRING",
    "NYTP_TAG_STRING_UTF8",
    "NYTP_TAG_TIME_LINE",
    "NYTP_TAG_PID_END",
    "KNOWN_TAGS",
]
