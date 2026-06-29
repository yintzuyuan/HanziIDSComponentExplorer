#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""glyph_font_runs：把文字切成 (子字串, 需逐字解析字型) 連續段的純函式（TDD）。

用於中欄結果列表的逐字選字型繪製：連續 ASCII 併段（用基準字型）、
每個非 ASCII 字各自一段（需 get_font_for_char 逐字解析，因 CJK／亞美尼亞／
PUA／樹狀符號可能各需不同字型）。
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

from hanzi_core import glyph_font_runs  # noqa: E402

E000 = chr(0xE000)


class TestGlyphFontRuns:
    def test_empty(self):
        assert glyph_font_runs("") == []

    def test_none(self):
        assert glyph_font_runs(None) == []

    def test_pure_ascii_is_single_run(self):
        assert glyph_font_runs("U+E000") == [("U+E000", False)]

    def test_single_cjk(self):
        assert glyph_font_runs("木") == [("木", True)]

    def test_single_pua(self):
        assert glyph_font_runs(E000) == [(E000, True)]

    def test_each_nonascii_is_its_own_run(self):
        # 非 ASCII 不合併（可能各需不同字型）
        assert glyph_font_runs("木林") == [("木", True), ("林", True)]

    def test_mixed_tree_prefix(self):
        # "├─ 木A"：兩個樹狀符號各自成段、空白併入 ASCII、木單獨、A 併 ASCII
        assert glyph_font_runs("├─ 木A") == [
            ("├", True),
            ("─", True),
            (" ", False),
            ("木", True),
            ("A", False),
        ]

    def test_leading_ascii_then_nonascii(self):
        assert glyph_font_runs("ab木") == [("ab", False), ("木", True)]

    def test_concatenation_roundtrip(self):
        text = "└─ " + E000 + "Ա xyz"
        assert "".join(seg for seg, _ in glyph_font_runs(text)) == text
