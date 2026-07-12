#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""choose_glyph_font_source：PUA 缺字字型解析的優先序決策純函式（TDD）。

_resolve_glyph_font 的四段優先序（#26 新增 folder tier）：
1) 參考字型資料夾內有字型涵蓋此碼位 → 用它（使用者明確意圖，蓋過一切自動推斷）；
2) 當前文件同名安裝字型「確實涵蓋」此碼位 → 用它（編輯中優先）；
3) 否則掃所有已安裝字型取涵蓋此碼位者 → 用它（與開哪個檔無關）；
4) 都沒有 → None（退系統字型、由負向快取記住待重試）。

健檢 #1 相扣修正：原末步誤回「已確認不涵蓋」的同名字型，會被 get_font_for_char
當正向結果 store()（sticky 豆腐、forget_missing 清不掉）。正確應回 None 走 store_missing。
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

from hanzi_core import choose_glyph_font_source  # noqa: E402


class TestChooseGlyphFontSource:
    """choose_glyph_font_source(folder_covers, family_covers, covering_found)
    → 'folder'|'family'|'covering'|None。"""

    def test_folder_covers_uses_folder(self):
        assert choose_glyph_font_source(True, False, False) == "folder"

    def test_folder_takes_priority_over_family_and_covering(self):
        # 資料夾是使用者明確放入的覆蓋意圖，優先於文件同名字型與已安裝字型
        assert choose_glyph_font_source(True, True, True) == "folder"

    def test_family_covers_uses_family(self):
        assert choose_glyph_font_source(False, True, False) == "family"

    def test_family_covers_takes_priority_over_covering(self):
        # 文件同名字型涵蓋時優先，即使另有涵蓋字型
        assert choose_glyph_font_source(False, True, True) == "family"

    def test_covering_found_when_family_not_cover(self):
        assert choose_glyph_font_source(False, False, True) == "covering"

    def test_none_when_nothing_covers(self):
        # 回歸核心：都不涵蓋 → None（不可退回不涵蓋的同名字型）
        assert choose_glyph_font_source(False, False, False) is None
