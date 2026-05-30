#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HanziCore.classify_by_position / format_position_label 測試

語意：對結果字按「頂層 IDC + 查詢部件出現位置」分組，作為右欄分組顯示的後端。

驗證範圍：
- fine：IDC + 位置數字 + ≡（多位），複用 _recursive_components 判斷子部件是否含查詢部件
- coarse：只看頂層 IDC、不分位置（多部件交集模式用）
- 嵌套：查詢部件嵌在頂層子部件內仍歸到「該子部件所在的頂層位置」
- 對稱：多個頂層位置都含查詢部件 → ≡（不重複出現）
- 邊緣：獨體字、變體（〾）、CDP 實體參考、無頂層 IDC
- format_position_label：渲染標籤的字面格式
"""

import sys
from pathlib import Path

import pytest

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
def core_position():
    """位置分組測試核心。

    所有 IDS 取自 CHISE IDS-UCS-Basic / Ext-B 真實資料：
        鐘 = ⿰金童                  金在 ⿰ 位置 1
        淦 = ⿰氵金                  金在 ⿰ 位置 2
        鍂 = ⿰金金                  金在 ⿰ 兩位皆直接（對稱）
        鑫 = ⿱金鍂                  金在 ⿱ 位置 1 直接、位置 2 透過鍂嵌套（對稱）
        𨰻 = ⿱⿰金金⿰金金          金在 ⿱ 兩位皆為含金的子結構（對稱）
        崟 = ⿱山金                  金在 ⿱ 位置 2
        鏖 = ⿸鹿金                  金在 ⿸ 位置 2（左上包圍）
        銜 = ⿴行金                  金在 ⿴ 位置 2（包圍）
        童 = ⿱立里                  立在 ⿱ 位置 1
        林 = ⿰木木                  木在 ⿰ 兩位皆直接（對稱）
        森 = ⿱木林                  木在 ⿱ 兩位（位置 2 透過林嵌套）
    """
    return _make_core(
        {
            # 葉部件
            "金": {"unicode": "91D1", "ids_1": "金"},
            "木": {"unicode": "6728", "ids_1": "木"},
            "火": {"unicode": "706B", "ids_1": "火"},
            "立": {"unicode": "7ACB", "ids_1": "立"},
            "田": {"unicode": "7530", "ids_1": "田"},
            "土": {"unicode": "571F", "ids_1": "土"},
            "氵": {"unicode": "6C35", "ids_1": "氵"},
            "山": {"unicode": "5C71", "ids_1": "山"},
            "鹿": {"unicode": "9E7F", "ids_1": "鹿"},
            "行": {"unicode": "884C", "ids_1": "行"},
            # 中間部件
            "里": {"unicode": "91CC", "ids_1": "⿱田土"},
            "童": {"unicode": "7AE5", "ids_1": "⿱立里"},
            "鍂": {"unicode": "9342", "ids_1": "⿰金金"},
            "林": {"unicode": "6797", "ids_1": "⿰木木"},
            # 測試對象
            "鐘": {"unicode": "9418", "ids_1": "⿰金童"},
            "淦": {"unicode": "6DE6", "ids_1": "⿰氵金"},
            "鑫": {"unicode": "946B", "ids_1": "⿱金鍂"},
            "𨰻": {"unicode": "28C3B", "ids_1": "⿱⿰金金⿰金金"},
            "崟": {"unicode": "5D1F", "ids_1": "⿱山金"},
            "鏖": {"unicode": "93D6", "ids_1": "⿸鹿金"},
            "銜": {"unicode": "929C", "ids_1": "⿴行金"},
            "森": {"unicode": "68EE", "ids_1": "⿱木林"},
        }
    )


class TestClassifyByPositionFine:
    """fine 模式：IDC + 位置數字（多位用 None 代表 ≡）"""

    def test_query_direct_left(self, core_position):
        """鐘 = ⿰金童；金在頂層位置 1（直接）"""
        assert core_position.classify_by_position("鐘", ["金"], "fine") == ("⿰", 1)

    def test_query_direct_right(self, core_position):
        """淦 = ⿰氵金；金在頂層位置 2（直接）"""
        assert core_position.classify_by_position("淦", ["金"], "fine") == ("⿰", 2)

    def test_query_symmetric_direct(self, core_position):
        """鍂 = ⿰金金；位置 1 和 2 都直接是金 → ≡"""
        assert core_position.classify_by_position("鍂", ["金"], "fine") == ("⿰", None)

    def test_query_symmetric_via_nested_char(self, core_position):
        """鑫 = ⿱金鍂；位置 1 直接是金、位置 2 是含金的子字鍂 → ⿱≡"""
        assert core_position.classify_by_position("鑫", ["金"], "fine") == ("⿱", None)

    def test_query_symmetric_via_substructure(self, core_position):
        """𨰻 = ⿱⿰金金⿰金金；兩位都是含金的 IDS 子結構 → ⿱≡"""
        assert core_position.classify_by_position("𨰻", ["金"], "fine") == ("⿱", None)

    def test_query_in_top_position_2(self, core_position):
        """崟 = ⿱山金；金在頂層位置 2（直接）"""
        assert core_position.classify_by_position("崟", ["金"], "fine") == ("⿱", 2)

    def test_query_in_enclosure(self, core_position):
        """鏖 = ⿸鹿金；金在 ⿸ 位置 2（左上包圍的內側）"""
        assert core_position.classify_by_position("鏖", ["金"], "fine") == ("⿸", 2)

    def test_query_full_enclosure(self, core_position):
        """銜 = ⿴行金；金在 ⿴ 位置 2"""
        assert core_position.classify_by_position("銜", ["金"], "fine") == ("⿴", 2)

    def test_query_only_in_nested_subcomponent(self, core_position):
        """鐘 中的「立」：鐘=⿰金童、童=⿱立里，立 嵌在童內 → 立在 ⿰ 位置 2"""
        assert core_position.classify_by_position("鐘", ["立"], "fine") == ("⿰", 2)

    def test_query_direct_in_intermediate_char(self, core_position):
        """童 = ⿱立里；立 直接在頂層位置 1"""
        assert core_position.classify_by_position("童", ["立"], "fine") == ("⿱", 1)

    def test_symmetric_wood(self, core_position):
        """林 = ⿰木木；木對稱 → ⿰≡"""
        assert core_position.classify_by_position("林", ["木"], "fine") == ("⿰", None)

    def test_nested_symmetric_wood(self, core_position):
        """森 = ⿱木林；位置 1 直接是木、位置 2 是含木的林 → ⿱≡"""
        assert core_position.classify_by_position("森", ["木"], "fine") == ("⿱", None)

    def test_independent_char_returns_empty_label(self, core_position):
        """獨體字（IDS 即自身）→ (∅, None)；衍生字流程下不應發生、僅 fallback"""
        assert core_position.classify_by_position("金", ["金"], "fine") == ("∅", None)


class TestClassifyByPositionCoarse:
    """coarse 模式：只看頂層 IDC、不解析位置（多部件交集模式用）"""

    def test_coarse_drops_position_left(self, core_position):
        """鐘 = ⿰金童；coarse 只回頂層 IDC，不分位置"""
        assert core_position.classify_by_position("鐘", ["金", "童"], "coarse") == (
            "⿰",
            None,
        )

    def test_coarse_top_idc_only(self, core_position):
        """鑫 = ⿱金鍂；coarse 模式只回 ⿱、不關心對稱與否"""
        assert core_position.classify_by_position("鑫", ["金"], "coarse") == (
            "⿱",
            None,
        )

    def test_coarse_enclosure(self, core_position):
        """鏖 = ⿸鹿金；coarse 回 ⿸"""
        assert core_position.classify_by_position("鏖", ["金"], "coarse") == (
            "⿸",
            None,
        )

    def test_coarse_independent_char(self, core_position):
        """獨體字 coarse 也回 ∅"""
        assert core_position.classify_by_position("金", ["金"], "coarse") == (
            "∅",
            None,
        )


class TestFormatPositionLabel:
    """format_position_label：渲染分組標籤的字面格式"""

    def test_position_1(self, core_position):
        assert core_position.format_position_label("⿰", 1) == "⿰1"

    def test_position_2(self, core_position):
        assert core_position.format_position_label("⿰", 2) == "⿰2"

    def test_position_3(self, core_position):
        """三位結構：⿲ 的位置 3"""
        assert core_position.format_position_label("⿲", 3) == "⿲3"

    def test_multi_position_uses_identical_to(self, core_position):
        """多位（None）渲染為 ⿰≡（U+2261）"""
        assert core_position.format_position_label("⿰", None) == "⿰≡"

    def test_variant_marker_label(self, core_position):
        """〾（變體）無位置數字、單獨呈現"""
        assert core_position.format_position_label("〾", None) == "〾"

    def test_empty_label_unclassified(self, core_position):
        """∅ fallback 標籤不加數字"""
        assert core_position.format_position_label("∅", None) == "∅"


class TestGroupByPositionFine:
    """group_by_position（fine）：依位置分組 + 標籤渲染 + 排序的整合行為。"""

    def test_fine_groups_with_idc_order_and_position_order(self, core_position):
        """fine 多種 IDC + 位置應依 IDC_ORDER（⿰<⿱<⿴<⿸…）與位置升序（1<2<≡）排，
        每組內字按 Unicode 升序、空組不出現。"""
        chars = ["鐘", "淦", "鍂", "鑫", "𨰻", "崟", "鏖", "銜"]
        groups = core_position.group_by_position(chars, ["金"], "fine")
        assert groups == [
            ("⿰1", ["鐘"]),
            ("⿰2", ["淦"]),
            ("⿰≡", ["鍂"]),
            ("⿱2", ["崟"]),
            ("⿱≡", ["鑫", "𨰻"]),  # 鑫(U+946B) < 𨰻(U+28C3B)
            ("⿴2", ["銜"]),
            ("⿸2", ["鏖"]),
        ]

    def test_fine_single_position_group(self, core_position):
        """單組情境：只有 ⿰1。"""
        assert core_position.group_by_position(["鐘"], ["金"], "fine") == [
            ("⿰1", ["鐘"])
        ]

    def test_fine_unclassified_falls_to_empty_label(self, core_position):
        """獨體字（金本身）→ ∅ 組。"""
        assert core_position.group_by_position(["金"], ["金"], "fine") == [
            ("∅", ["金"])
        ]

    def test_fine_empty_input_returns_empty(self, core_position):
        assert core_position.group_by_position([], ["金"], "fine") == []


class TestGroupByPositionCoarse:
    """group_by_position（coarse）：標籤只用 IDC 字元、不加位置/≡。"""

    def test_coarse_uses_plain_idc_label(self, core_position):
        """coarse：⿰、⿱、⿸ 等只用 IDC 字元當 label。"""
        chars = ["鐘", "鑫", "鏖"]
        groups = core_position.group_by_position(chars, ["金", "童"], "coarse")
        assert groups == [
            ("⿰", ["鐘"]),
            ("⿱", ["鑫"]),
            ("⿸", ["鏖"]),
        ]

    def test_coarse_symmetric_chars_dont_get_identity(self, core_position):
        """coarse：鍂 = ⿰金金 仍歸 ⿰，不會升為 ⿰≡。"""
        groups = core_position.group_by_position(["鍂", "鐘"], ["金"], "coarse")
        assert groups == [("⿰", ["鍂", "鐘"])]  # 鍂 U+9342 < 鐘 U+9418
