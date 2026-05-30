#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resolve_display_char：決定右欄顯示哪個字的純函式。

語意：UI 多個 callback（stroke filter、color filter、refresh）共用一個 fallback 順序——
明示參數 > sticky（上次右欄顯示、由 selection_callback 寫入）> current（左欄/本字）。

此純函式 cover「子部件視角下、無 char 參數的 callback 不該跳回本字」這個 UI bug
的核心邏輯；UI state init / reset 行為靠實機驗證。
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

from hanzi_core import resolve_display_char  # noqa: E402


class TestResolveDisplayChar:
    """resolve_display_char(char, sticky, current) → Optional[str]"""

    def test_explicit_char_wins_over_all(self):
        """明示 char 永遠優先（即使 sticky、current 也都有）。"""
        assert resolve_display_char("明", "日", "金") == "明"

    def test_sticky_overrides_current_when_no_char(self):
        """無 char 時、sticky（上次右欄顯示）優先於 current（本字）。
        這是修「子部件視角下 stroke filter 跳回本字」bug 的核心：
        selection_callback 點「日」後 sticky=日，stroke filter 觸發
        update_related_display(None) 仍顯示日視角、不退回本字（金）。
        """
        assert resolve_display_char(None, "日", "金") == "日"

    def test_current_as_fallback_when_no_sticky(self):
        """無 char 也無 sticky（如剛搜尋完、未點任何子部件）：用 current 本字。"""
        assert resolve_display_char(None, None, "金") == "金"

    def test_all_none_returns_none(self):
        """三者皆 None：回 None（UI 端 caller 應 early return）。"""
        assert resolve_display_char(None, None, None) is None

    def test_empty_sticky_falls_through_to_current(self):
        """sticky 為空字串（falsy）：跳過、用 current。
        （實際上 sticky 不會是空字串，但 or 邏輯需明確）"""
        assert resolve_display_char(None, "", "金") == "金"

    def test_explicit_char_is_distinguished_from_none(self):
        """明示傳 char='永' 即使 sticky/current 都是別字、仍用 '永'。"""
        assert resolve_display_char("永", "日", "金") == "永"
