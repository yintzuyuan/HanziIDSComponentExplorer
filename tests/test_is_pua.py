#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""is_pua：私有使用區碼位判定純函式（TDD，#26）。

PUA 碼位的字型解析不可信任系統 cascade（任何字型對 PUA 的涵蓋都是各自為政），
get_font_for_char 以此函式將 PUA 分流到明確優先序路徑。
範圍：BMP U+E000–F8FF、Plane 15 U+F0000–FFFFD、Plane 16 U+100000–10FFFD
（各補充平面最末兩碼位為 noncharacter，不含）。
"""

import sys
from pathlib import Path

PLUGIN_RESOURCES = (
    Path(__file__).parent.parent
    / "HanziIDSComponentExplorer.glyphsPlugin"
    / "Contents"
    / "Resources"
)
sys.path.insert(0, str(PLUGIN_RESOURCES))

from hanzi_core import is_pua  # noqa: E402


class TestIsPuaBmp:
    def test_bmp_pua_start(self):
        assert is_pua(0xE000)

    def test_bmp_pua_end(self):
        assert is_pua(0xF8FF)

    def test_below_bmp_pua_is_not(self):
        assert not is_pua(0xDFFF)

    def test_compat_ideograph_above_bmp_pua_is_not(self):
        assert not is_pua(0xF900)


class TestIsPuaSupplementary:
    def test_plane15_start(self):
        assert is_pua(0xF0000)

    def test_plane15_end(self):
        assert is_pua(0xFFFFD)

    def test_plane15_noncharacter_excluded(self):
        assert not is_pua(0xFFFFE)

    def test_plane16_start(self):
        assert is_pua(0x100000)

    def test_plane16_end(self):
        assert is_pua(0x10FFFD)

    def test_plane16_noncharacter_excluded(self):
        assert not is_pua(0x10FFFE)

    def test_below_plane15_is_not(self):
        assert not is_pua(0xEFFFF)


class TestIsPuaCommonChars:
    def test_cjk_unified_is_not(self):
        assert not is_pua(0x4E00)

    def test_ascii_is_not(self):
        assert not is_pua(0x41)

    def test_cjk_ext_b_is_not(self):
        assert not is_pua(0x20000)
