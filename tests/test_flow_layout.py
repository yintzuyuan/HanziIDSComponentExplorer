#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flow_layout：底部控制列流式排版的純函式（Issue #23）。

把「由左到右依序擺放可變寬度元件」的位置計算抽成純函式做 TDD，
UI 黏合（量測各語言 label 實際寬度、setPosSize）靠實機。

回傳 (positions, next_x)：
- positions 與 widths 對應，每個 (x, width)
- next_x 是最後一個元件之後（含一個尾隨 gap）的下一個起始 x，
  供滑桿左緣接續；widths 為空時等於 start_x。
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

from hanzi_core import flow_layout  # noqa: E402


class TestFlowLayout:
    """flow_layout(start_x, widths, gap) -> (positions, next_x)"""

    def test_empty_widths_returns_no_positions_and_start_x(self):
        """無元件 → 空位置清單，next_x 等於起點（不含尾隨 gap）。"""
        positions, next_x = flow_layout(114, [], gap=8)
        assert positions == []
        assert next_x == 114

    def test_single_element_position_and_next_x_includes_gap(self):
        """單一元件 → 落在 start_x，next_x = start_x + width + gap。"""
        positions, next_x = flow_layout(114, [80], gap=8)
        assert positions == [(114, 80)]
        assert next_x == 202  # 114 + 80 + 8

    def test_multiple_elements_accumulate_left_to_right(self):
        """多元件 → 依序累加，每個前面隔一個 gap。"""
        positions, next_x = flow_layout(114, [106, 66], gap=8)
        assert positions == [(114, 106), (228, 66)]  # 第二個 = 114 + 106 + 8
        assert next_x == 302  # 228 + 66 + 8

    def test_zero_gap_packs_tightly(self):
        """gap=0 → 元件緊貼，next_x 不含間距。"""
        positions, next_x = flow_layout(0, [50, 30], gap=0)
        assert positions == [(0, 50), (50, 30)]
        assert next_x == 80

    def test_float_widths_preserved(self):
        """sizeToFit 回傳 float 寬度 → 位置算術保留浮點，不取整。"""
        positions, next_x = flow_layout(10.0, [20.5, 15.25], gap=4.0)
        assert positions == [(10.0, 20.5), (34.5, 15.25)]  # 10 + 20.5 + 4
        assert next_x == 53.75  # 34.5 + 15.25 + 4
