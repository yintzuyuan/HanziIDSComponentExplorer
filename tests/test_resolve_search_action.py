#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resolve_search_action：決定搜尋框 callback 該做什麼動作的純函式。

統一 #21（無字型閘門）與 #22（清空回到當前字／清空白）兩個 UI bug 的決策邏輯：
搜尋框 callback 只計算 runtime 布林值、由此純函式決定動作字串，再 dispatch。
UI 黏合（顯示提示、清三欄、取當前選字）靠實機驗證。

動作語意：
- "auto"   清空輸入且當前有選中字 → 回到自動模式顯示該字
- "clear"  清空輸入且無選中字 → 三欄清成空白
- "noop"   非空但輸入未完整 → 維持現狀等待
- "gate"   非空且完整、但未開字型 → 閘門擋下（不查全庫），顯示提示
- "search" 非空、完整、已開字型 → 執行搜尋
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

from hanzi_core import resolve_search_action  # noqa: E402


class TestResolveSearchAction:
    """resolve_search_action(input_text, font_open, has_selected_char, is_complete) -> str"""

    # === 清空輸入（#22）===

    def test_empty_input_with_selected_char_returns_auto(self):
        """清空搜尋框且當前有選中字 → 回到自動模式顯示該字。"""
        assert (
            resolve_search_action("", font_open=True, has_selected_char=True, is_complete=False)
            == "auto"
        )

    def test_empty_input_without_selected_char_returns_clear(self):
        """清空搜尋框且當前無選中字 → 三欄清空。"""
        assert (
            resolve_search_action("", font_open=True, has_selected_char=False, is_complete=False)
            == "clear"
        )

    def test_whitespace_only_input_is_treated_as_empty(self):
        """純空白視同清空（resolver 內部 strip）。"""
        assert (
            resolve_search_action("   ", font_open=True, has_selected_char=True, is_complete=False)
            == "auto"
        )

    def test_empty_input_without_font_returns_clear(self):
        """無開檔時清空 → 無當前字 → 清空白（不會誤觸全庫查詢）。"""
        assert (
            resolve_search_action("", font_open=False, has_selected_char=False, is_complete=False)
            == "clear"
        )

    # === 非空輸入（#21 閘門 + 既有搜尋）===

    def test_complete_input_with_font_returns_search(self):
        """完整輸入且已開字型 → 正常搜尋。"""
        assert (
            resolve_search_action("信", font_open=True, has_selected_char=False, is_complete=True)
            == "search"
        )

    def test_complete_input_without_font_returns_gate(self):
        """完整輸入但未開字型 → 閘門擋下（#21：避免對整個 IDS 資料庫查詢而崩潰）。"""
        assert (
            resolve_search_action("信", font_open=False, has_selected_char=False, is_complete=True)
            == "gate"
        )

    def test_incomplete_input_returns_noop(self):
        """非空但輸入未完整 → 維持現狀（既有行為）。"""
        assert (
            resolve_search_action("U+", font_open=True, has_selected_char=False, is_complete=False)
            == "noop"
        )

    def test_incomplete_input_without_font_still_noop(self):
        """未完整輸入優先於閘門：尚未要查詢，不需提示開檔。"""
        assert (
            resolve_search_action("U+", font_open=False, has_selected_char=False, is_complete=False)
            == "noop"
        )
