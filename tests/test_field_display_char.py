#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""field_display_char：決定搜尋框該以哪個字的字型渲染的純函式（TDD）。

NSSearchField 整欄只能單一字型，故策略為：
1) 含造字（PUA）→ 用第一個 PUA 字（系統字型必缺、最該優先顯示）；
2) 否則整段非 ASCII（CJK／亞美尼亞等）→ 用首字；
3) 含 ASCII（如 U+XXXX 十六進位查詢）且無 PUA → None（維持系統字型）。
PUA 碼位以 chr(0xXXXX) 明確表達，不放字面不可見字元。
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

from hanzi_core import field_display_char  # noqa: E402

E000 = chr(0xE000)
E001 = chr(0xE001)
AYB = chr(0x0531)  # Ա
PEH = chr(0x054A)  # Պ
TIWN = chr(0x054F)  # Տ


class TestFieldDisplayChar:
    def test_empty_returns_none(self):
        assert field_display_char("") is None

    def test_none_returns_none(self):
        assert field_display_char(None) is None

    def test_whitespace_returns_none(self):
        assert field_display_char("   ") is None

    def test_ascii_unicode_query_returns_none(self):
        # 十六進位查詢字串（純 ASCII、無實際造字）→ 不改字型
        assert field_display_char("U+E000") is None

    def test_bare_hex_returns_none(self):
        assert field_display_char("E000") is None

    def test_single_ascii_returns_none(self):
        assert field_display_char("5") is None

    def test_single_pua_char(self):
        assert field_display_char(E000) == E000

    def test_single_armenian_char(self):
        assert field_display_char(AYB) == AYB

    def test_multi_nonascii_no_pua_uses_first(self):
        # 無 PUA、整段非 ASCII → 用首字
        assert field_display_char(PEH + TIWN) == PEH

    def test_cjk_uses_first(self):
        assert field_display_char("氵木") == "氵"

    def test_pua_wins_over_leading_ascii(self):
        # 含實際造字（PUA）→ 即使前面有 ASCII，也用該造字驅動欄位字型
        assert field_display_char("U+" + E000) == E000

    def test_pua_wins_over_leading_cjk(self):
        # 含造字 → 優先於前導 CJK（單一字型欄位，造字最該顯示）
        assert field_display_char("木" + E000) == E000

    def test_returns_first_pua_when_multiple(self):
        assert field_display_char(E000 + "木" + E001) == E000

    def test_strips_surrounding_whitespace(self):
        assert field_display_char("  " + AYB + "  ") == AYB
