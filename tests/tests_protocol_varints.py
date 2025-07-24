import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from pynytprof.protocol import (
    write_u32,
    write_i32,
    write_tag_u32,
    read_u32,
    read_i32,
)


@pytest.mark.parametrize(
    "val",
    [
        0,
        1,
        0x7F,
        0x80 - 1,
        0x80,
        0x3FFF,
        0x4000,
        0x1FFFFF,
        0x200000,
        0x0FFFFFFF,
        0x10000000,
        0xFFFFFFFF,
    ],
)
def test_u32_roundtrip(val):
    encoded = write_u32(val)
    decoded, off = read_u32(encoded, 0)
    assert off == len(encoded)
    assert decoded == val


@pytest.mark.parametrize(
    "val",
    [
        0,
        -1,
        1,
        -0x80,
        -0x4000,
        -0x200000,
        -0x10000000,
        -0x80000000,
        0x7FFFFFFF,
    ],
)
def test_i32_roundtrip(val):
    encoded = write_i32(val)
    decoded, off = read_i32(encoded, 0)
    assert off == len(encoded)
    assert decoded == val


def test_tag_prefix_added():
    val = 0x1234
    plain = write_u32(val)
    tagged = write_tag_u32(0x42, val)
    assert tagged[0] == 0x42
    assert tagged[1:] == plain
    assert len(tagged) == len(plain) + 1

