#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""utf16_len：字串的 UTF-16 碼元長度純函式（TDD）。

CoreText 的 CTFontCreateForString range 以 UTF-16 計量；Python len() 以碼位計量。
補充平面字（如 CJK Ext-B、補充平面 PUA U+F0000）在 UTF-16 為代理對（2 碼元），
若用 len()（=1）只涵蓋前導代理 → last_resort 偵測失準。此函式回正確 UTF-16 長度。
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

from hanzi_core import utf16_len  # noqa: E402


class TestUtf16Len:
    def test_ascii_is_one(self):
        assert utf16_len("A") == 1

    def test_bmp_cjk_is_one(self):
        assert utf16_len("漢") == 1

    def test_bmp_pua_is_one(self):
        assert utf16_len(chr(0xE000)) == 1

    def test_astral_is_two(self):
        # 補充表意平面 CJK Ext-B
        assert utf16_len(chr(0x20000)) == 2

    def test_astral_pua_is_two(self):
        # 補充平面 PUA（Plane 15）
        assert utf16_len(chr(0xF0000)) == 2

    def test_empty_is_zero(self):
        assert utf16_len("") == 0

    def test_mixed_sums_codeunits(self):
        # "A" + BMP "漢" + astral → 1 + 1 + 2
        assert utf16_len("A漢" + chr(0x20000)) == 4
