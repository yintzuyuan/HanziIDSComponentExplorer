#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HanziCore 多部件 AND 搜尋（search_all）測試

語意：將候選字「遞迴展開到葉部件」後，其部件計數需涵蓋查詢的多重集計數。
- 遞迴：「淋」=⿰氵林，木藏在林裡（第二層），查「氵木」仍應命中（問題 1）。
- 計數：查「木木」代表「至少兩個木」，林(2木)、森(3木) 命中，沐(1木) 不命中（問題 2）。
以記憶體 fixture 精確控制多層部件結構，驗證遞迴展開與計數匹配。
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
    """建立跳過檔案載入的 HanziCore（測試專用），直接注入內部格式資料庫。"""
    core = HanziCore.__new__(HanziCore)
    core.data_path = Path("__test_in_memory__")
    core._parsed_ids_cache = {}
    core.db = {}
    for char, data in records.items():
        core.db[char] = {
            "unicode": data.get("unicode", ""),
            "char": char,
            "ids_1": data.get("ids_1", ""),
            "ids_2": data.get("ids_2", ""),
            "strokes": data.get("strokes"),
        }
    core._build_indexes()
    return core


@pytest.fixture
def core_components():
    """多層部件交集測試核心。

    IDS 為測試構造（部件採常規漢字，不受 NFKC 正規化影響）。
    遞迴展開到葉部件後的計數：
        林 → {木:2}            （⿰木木）
        沐 → {氵:1, 木:1}      （⿰氵木）
        淋 → {氵:1, 木:2}      （⿰氵林 → 氵 + 木木，木藏在第二層）
        森 → {木:3}            （⿱木林 → 木 + 木木）
        村 → {木:1, 寸:1}      （⿰木寸）
    """
    return _make_core(
        {
            "木": {"unicode": "6728", "ids_1": "木"},
            "氵": {"unicode": "6C35", "ids_1": "氵"},
            "寸": {"unicode": "5BF8", "ids_1": "寸"},
            "林": {"unicode": "6797", "ids_1": "⿰木木"},
            "沐": {"unicode": "6C90", "ids_1": "⿰氵木"},
            "淋": {"unicode": "6DCB", "ids_1": "⿰氵林"},
            "森": {"unicode": "68EE", "ids_1": "⿱木林"},
            "村": {"unicode": "6751", "ids_1": "⿰木寸"},
        }
    )


class TestSearchAllRecursive:
    """遞迴展開：木藏在更深層級時仍應命中（解決問題 1）"""

    def test_matches_via_nested_component(self, core_components):
        """「氵木」：淋=⿰氵林，木在第二層，仍應命中（連同直接含木的沐）"""
        result = core_components.search_all(["氵", "木"])
        assert set(result) == {"沐", "淋"}

    def test_single_query_recursive_holders(self, core_components):
        """單部件「木」：所有遞迴含木的字（含木自身，與 search 一致）。

        淋=⿰氵林 透過林（⿰木木）遞迴含木，亦應命中。
        """
        assert set(core_components.search_all(["木"])) == {
            "木",
            "林",
            "沐",
            "淋",
            "森",
            "村",
        }


class TestSearchAllCounting:
    """多重集計數：重複部件代表「至少 N 個」（解決問題 2）"""

    def test_double_component_requires_at_least_two(self, core_components):
        """「木木」= 至少兩個木：林(2)、淋(2)、森(3) 命中；沐(1)、村(1) 不命中"""
        assert set(core_components.search_all(["木", "木"])) == {"林", "淋", "森"}

    def test_triple_component_requires_at_least_three(self, core_components):
        """「木木木」= 至少三個木：只有森(3) 命中"""
        assert core_components.search_all(["木", "木", "木"]) == ["森"]

    def test_mixed_count_and_distinct(self, core_components):
        """「氵木木」= 氵≥1 且 木≥2：只有淋(氵1,木2) 命中；沐(木1) 不命中"""
        assert core_components.search_all(["氵", "木", "木"]) == ["淋"]


class TestSearchAllGeneral:
    """通用契約：空輸入、charset、排序"""

    def test_empty_queries_returns_empty(self, core_components):
        assert core_components.search_all([]) == []

    def test_empty_intersection_returns_empty(self, core_components):
        """無字同時含氵與寸 → 空"""
        assert core_components.search_all(["氵", "寸"]) == []

    def test_charset_filter_applied(self, core_components):
        """charset 篩選後只保留字集內的字"""
        result = core_components.search_all(["木", "木"], charset={"林"})
        assert result == ["林"]

    def test_results_sorted_by_codepoint(self, core_components):
        """結果按 Unicode 碼位升序"""
        result = core_components.search_all(["木", "木"])
        assert result == sorted(result, key=ord)


@pytest.fixture
def core_intermediate():
    """中間部件交集測試核心。

    中間部件＝本身可再拆、卻仍是常用查詢詞的部件（里、童、林）。
    遞迴展開到「所有層級節點」後的計數（含中間節點與根字自身）：
        里 → {里:1, 田:1, 土:1}                （⿱田土）
        林 → {林:1, 木:2}                       （⿰木木）
        童 → {童:1, 立:1, 里:1, 田:1, 土:1}      （⿱立里）
        鐘 → {鐘:1, 金:1, 童:1, 立:1, 里:1, ...} （⿰金童，深層含立、里）
        焚 → {焚:1, 林:1, 木:2, 火:1}            （⿱林火）
    """
    return _make_core(
        {
            "木": {"unicode": "6728", "ids_1": "木"},
            "火": {"unicode": "706B", "ids_1": "火"},
            "立": {"unicode": "7ACB", "ids_1": "立"},
            "田": {"unicode": "7530", "ids_1": "田"},
            "土": {"unicode": "571F", "ids_1": "土"},
            "金": {"unicode": "91D1", "ids_1": "金"},
            "里": {"unicode": "91CC", "ids_1": "⿱田土"},
            "林": {"unicode": "6797", "ids_1": "⿰木木"},
            "童": {"unicode": "7AE5", "ids_1": "⿱立里"},
            "鐘": {"unicode": "9418", "ids_1": "⿰金童"},
            "焚": {"unicode": "711A", "ids_1": "⿱林火"},
        }
    )


class TestSearchAllIntermediateComponents:
    """中間部件可比對：查詢詞本身可再拆時，仍應命中含它的字（修復回報的 bug）"""

    def test_intermediate_component_li_matches_tong(self, core_intermediate):
        """「立里」：里=⿱田土 是中間部件，童=⿱立里 應命中；鐘 深層亦含立、里"""
        assert set(core_intermediate.search_all(["立", "里"])) == {"童", "鐘"}

    def test_intermediate_component_tong_matches_zhong(self, core_intermediate):
        """「金童」：童=⿱立里 是中間部件，鐘=⿰金童 應命中"""
        assert core_intermediate.search_all(["金", "童"]) == ["鐘"]

    def test_intermediate_component_lin_matches_fen(self, core_intermediate):
        """「火林」：林=⿰木木 是中間部件，焚=⿱林火 應命中"""
        assert core_intermediate.search_all(["火", "林"]) == ["焚"]

    def test_leaf_path_still_matches_fen(self, core_intermediate):
        """回歸：「火木木」走葉部件路徑仍命中焚（火≥1 且 木≥2）"""
        assert core_intermediate.search_all(["火", "木", "木"]) == ["焚"]

    def test_mixed_intermediate_and_leaf(self, core_intermediate):
        """「木林」：木(葉)≥1 且 林(中間)≥1 → 林自身(木2,林1)與焚(木2,林1)命中"""
        assert set(core_intermediate.search_all(["木", "林"])) == {"林", "焚"}
