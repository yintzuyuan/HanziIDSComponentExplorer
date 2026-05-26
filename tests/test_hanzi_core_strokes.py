#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HanziCore 筆畫篩選 API 測試

涵蓋 get_stroke_count 與 filter_by_strokes 的所有情境，
包含資料缺值與向後相容（舊資料庫無 strokes 欄位）。
"""

import sys
from pathlib import Path

import pytest

# 將外掛 Resources 目錄加入路徑
PLUGIN_RESOURCES = (
    Path(__file__).parent.parent
    / "HanziIDSComponentExplorer.glyphsPlugin"
    / "Contents"
    / "Resources"
)
sys.path.insert(0, str(PLUGIN_RESOURCES))

from hanzi_core import HanziCore  # noqa: E402


def _make_core(records: dict) -> HanziCore:
    """建立一個跳過檔案載入的 HanziCore 實例（測試專用）。

    直接以內部格式注入資料庫，避免依賴 ids.pdata 檔案。
    內部格式：{字: {unicode, char, ids_1, ids_2, strokes}}
    """
    core = HanziCore.__new__(HanziCore)
    core.data_path = Path("__test_in_memory__")
    core._parsed_ids_cache = {}
    # 內部格式需要 char 欄位
    core.db = {}
    for char, data in records.items():
        core.db[char] = {
            "unicode": data.get("unicode", ""),
            "char": char,
            "ids_1": data.get("ids_1", ""),
            "ids_2": data.get("ids_2", ""),
            "strokes": data.get("strokes"),  # 可能為 None
        }
    core._build_indexes()
    return core


def _make_legacy_core(records: dict) -> HanziCore:
    """模擬舊版資料庫：完全沒有 strokes 鍵。"""
    core = HanziCore.__new__(HanziCore)
    core.data_path = Path("__test_in_memory_legacy__")
    core._parsed_ids_cache = {}
    core.db = {}
    for char, data in records.items():
        core.db[char] = {
            "unicode": data.get("unicode", ""),
            "char": char,
            "ids_1": data.get("ids_1", ""),
            "ids_2": data.get("ids_2", ""),
            # 故意不放 strokes 鍵
        }
    core._build_indexes()
    return core


@pytest.fixture
def core_with_strokes():
    """含 strokes 欄位的測試 HanziCore。

    測試字（簡化的筆畫數）：
        一=1, 二=2, 三=3, 五=4, 六=6, 七=7, 十=10
        無=None（資料缺值）
    """
    return _make_core(
        {
            "一": {"unicode": "4E00", "ids_1": "一", "strokes": 1},
            "二": {"unicode": "4E8C", "ids_1": "二", "strokes": 2},
            "三": {"unicode": "4E09", "ids_1": "三", "strokes": 3},
            "五": {"unicode": "4E94", "ids_1": "五", "strokes": 4},
            "六": {"unicode": "516D", "ids_1": "六", "strokes": 6},
            "七": {"unicode": "4E03", "ids_1": "七", "strokes": 7},
            "十": {"unicode": "5341", "ids_1": "十", "strokes": 10},
            "無": {"unicode": "7121", "ids_1": "無", "strokes": None},
        }
    )


@pytest.fixture
def core_legacy_no_strokes():
    """模擬舊版 ids.pdata：完全沒有 strokes 欄位。"""
    return _make_legacy_core(
        {
            "一": {"unicode": "4E00", "ids_1": "一"},
            "二": {"unicode": "4E8C", "ids_1": "二"},
            "三": {"unicode": "4E09", "ids_1": "三"},
        }
    )


class TestGetStrokeCount:
    """測試 get_stroke_count 查詢"""

    def test_returns_int_for_known_char(self, core_with_strokes):
        assert core_with_strokes.get_stroke_count("六") == 6

    def test_returns_one_for_single_stroke(self, core_with_strokes):
        assert core_with_strokes.get_stroke_count("一") == 1

    def test_returns_none_for_missing_data(self, core_with_strokes):
        """字在資料庫但 strokes 為 None"""
        assert core_with_strokes.get_stroke_count("無") is None

    def test_returns_none_for_unknown_char(self, core_with_strokes):
        """字不在資料庫"""
        assert core_with_strokes.get_stroke_count("龘") is None

    def test_returns_none_for_legacy_data(self, core_legacy_no_strokes):
        """舊版資料無 strokes 鍵，應回 None 而非報錯"""
        assert core_legacy_no_strokes.get_stroke_count("一") is None


class TestFilterByStrokes:
    """測試 filter_by_strokes 篩選"""

    def test_max_diff_none_returns_all(self, core_with_strokes):
        """max_diff=None → 不篩選，全部回傳"""
        chars = ["一", "二", "三", "六", "無"]
        result = core_with_strokes.filter_by_strokes(
            chars, base_char="三", max_diff=None
        )
        assert result == chars

    def test_max_diff_zero_returns_exact_match(self, core_with_strokes):
        """max_diff=0 → 只回傳筆畫完全相同的字"""
        chars = ["一", "二", "三", "六"]
        # base 三=3，只有 三 自己符合
        result = core_with_strokes.filter_by_strokes(chars, base_char="三", max_diff=0)
        assert result == ["三"]

    def test_max_diff_two_returns_within_range(self, core_with_strokes):
        """max_diff=2 → ±2 範圍：base 五(4) → 二(2)、三(3)、五(4)、六(6)"""
        chars = ["一", "二", "三", "五", "六", "七", "十"]
        result = core_with_strokes.filter_by_strokes(chars, base_char="五", max_diff=2)
        assert result == ["二", "三", "五", "六"]

    def test_excludes_chars_with_missing_data(self, core_with_strokes):
        """有資料的字依規則篩選，無 strokes 資料的字直接排除"""
        chars = ["一", "二", "三", "無"]
        result = core_with_strokes.filter_by_strokes(chars, base_char="二", max_diff=1)
        # base 二=2，±1 → 一(1)、二(2)、三(3) 都通過；無 被排除
        assert result == ["一", "二", "三"]
        assert "無" not in result

    def test_base_char_missing_data_returns_all(self, core_with_strokes):
        """主字無筆畫資料時，回退為全顯示，避免空白面板"""
        chars = ["一", "二", "三"]
        result = core_with_strokes.filter_by_strokes(chars, base_char="無", max_diff=1)
        assert result == chars

    def test_base_char_unknown_returns_all(self, core_with_strokes):
        """主字根本不在資料庫時，同樣回退為全顯示"""
        chars = ["一", "二", "三"]
        result = core_with_strokes.filter_by_strokes(chars, base_char="龘", max_diff=0)
        assert result == chars

    def test_empty_input_returns_empty(self, core_with_strokes):
        """空輸入 → 空回傳"""
        result = core_with_strokes.filter_by_strokes([], base_char="三", max_diff=2)
        assert result == []

    def test_legacy_data_with_filter_off(self, core_legacy_no_strokes):
        """舊資料 + 不篩選 → 全顯示"""
        chars = ["一", "二", "三"]
        result = core_legacy_no_strokes.filter_by_strokes(
            chars, base_char="一", max_diff=None
        )
        assert result == chars

    def test_legacy_data_base_missing_returns_all(self, core_legacy_no_strokes):
        """舊資料 + 開啟篩選 → 主字無資料 → 回退全顯示"""
        chars = ["一", "二", "三"]
        result = core_legacy_no_strokes.filter_by_strokes(
            chars, base_char="一", max_diff=2
        )
        assert result == chars

    def test_preserves_input_order(self, core_with_strokes):
        """結果順序應與輸入順序一致"""
        chars = ["六", "一", "三", "二"]
        result = core_with_strokes.filter_by_strokes(chars, base_char="二", max_diff=2)
        # base 二=2，±2 → 六(6) 不通過、一(1)、三(3)、二(2) 通過
        assert result == ["一", "三", "二"]


class TestFilterByStrokeValue:
    """測試 filter_by_stroke_value（數值基準篩選，多部件搜尋以部件筆畫加總為基準）"""

    def test_none_max_diff_returns_all(self, core_with_strokes):
        """max_diff=None → 不篩選，全部回傳"""
        chars = ["一", "二", "三"]
        assert core_with_strokes.filter_by_stroke_value(chars, 7, None) == chars

    def test_none_base_returns_all(self, core_with_strokes):
        """基準為 None（如部件無筆畫資料）→ 回退全顯示"""
        chars = ["一", "二", "三"]
        assert core_with_strokes.filter_by_stroke_value(chars, None, 2) == chars

    def test_exact_match(self, core_with_strokes):
        """base=7, max_diff=0 → 只保留 7 畫（七）"""
        chars = ["一", "二", "三", "五", "六", "七", "十"]
        assert core_with_strokes.filter_by_stroke_value(chars, 7, 0) == ["七"]

    def test_within_range(self, core_with_strokes):
        """base=4, max_diff=2 → 2~6 畫：二(2)、三(3)、五(4)、六(6)"""
        chars = ["一", "二", "三", "五", "六", "七", "十"]
        result = core_with_strokes.filter_by_stroke_value(chars, 4, 2)
        assert result == ["二", "三", "五", "六"]

    def test_excludes_missing_stroke_data(self, core_with_strokes):
        """無筆畫資料的字一律排除"""
        chars = ["一", "二", "無"]
        result = core_with_strokes.filter_by_stroke_value(chars, 2, 1)
        assert "無" not in result

    def test_preserves_order(self, core_with_strokes):
        """結果順序與輸入一致"""
        chars = ["六", "一", "三", "二"]
        # base=2 ±2 → 0~4：六(6) 排除；一(1)、三(3)、二(2) 通過
        assert core_with_strokes.filter_by_stroke_value(chars, 2, 2) == [
            "一",
            "三",
            "二",
        ]
