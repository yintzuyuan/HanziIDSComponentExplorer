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
            "永": {"unicode": "6C38", "ids_1": "永"},
            "雨": {"unicode": "96E8", "ids_1": "雨"},
            "月": {"unicode": "6708", "ids_1": "月"},
            "艹": {"unicode": "8279", "ids_1": "艹"},
            "言": {"unicode": "8A00", "ids_1": "言"},
            "𦍌": {"unicode": "2634C", "ids_1": "𦍌"},
            # 中間部件
            "里": {"unicode": "91CC", "ids_1": "⿱田土"},
            "童": {"unicode": "7AE5", "ids_1": "⿱立里"},
            "鍂": {"unicode": "9342", "ids_1": "⿰金金"},
            "林": {"unicode": "6797", "ids_1": "⿰木木"},
            "詠": {"unicode": "8A60", "ids_1": "⿰言永"},
            # 測試對象
            "鐘": {"unicode": "9418", "ids_1": "⿰金童"},
            "淦": {"unicode": "6DE6", "ids_1": "⿰氵金"},
            "鑫": {"unicode": "946B", "ids_1": "⿱金鍂"},
            "𨰻": {"unicode": "28C3B", "ids_1": "⿱⿰金金⿰金金"},
            "崟": {"unicode": "5D1F", "ids_1": "⿱山金"},
            "鏖": {"unicode": "93D6", "ids_1": "⿸鹿金"},
            "銜": {"unicode": "929C", "ids_1": "⿴行金"},
            "森": {"unicode": "68EE", "ids_1": "⿱木林"},
            # 永 系列（用於 is_nested 直接 vs 嵌套區分）
            "羕": {"unicode": "7F95", "ids_1": "⿱𦍌永"},
            "霡": {"unicode": "9721", "ids_1": "⿱雨⿰月永"},
            "𦻑": {"unicode": "26ED1", "ids_1": "⿱艹詠"},
            # 明 系列（用於 compose_immediate_component_lines 測試）
            "日": {"unicode": "65E5", "ids_1": "日"},
            "音": {"unicode": "97F3", "ids_1": "音"},
            "軍": {"unicode": "8ECD", "ids_1": "軍"},
            "冥": {"unicode": "51A5", "ids_1": "冥"},
            "卬": {"unicode": "536C", "ids_1": "卬"},
            "仄": {"unicode": "4EC4", "ids_1": "仄"},
            "一": {"unicode": "4E00", "ids_1": "一"},
            "匕": {"unicode": "5315", "ids_1": "匕"},
            "氏": {"unicode": "6C0F", "ids_1": "氏"},
            "良": {"unicode": "826F", "ids_1": "良"},
            "其": {"unicode": "5176", "ids_1": "其"},
            "公": {"unicode": "516C", "ids_1": "公"},
            "邦": {"unicode": "90A6", "ids_1": "邦"},
            "追": {"unicode": "8FFD", "ids_1": "追"},
            "芒": {"unicode": "8292", "ids_1": "芒"},
            "明": {"unicode": "660E", "ids_1": "⿰日月"},
            "暗": {"unicode": "6697", "ids_1": "⿰日音"},
            "暉": {"unicode": "6689", "ids_1": "⿰日軍"},
            "暝": {"unicode": "669D", "ids_1": "⿰日冥"},
            "昂": {"unicode": "6602", "ids_1": "⿱日卬"},  # ⿱ 結構、filter 排除
            "昃": {"unicode": "6603", "ids_1": "⿱日仄"},  # ⿱、排除
            "旦": {"unicode": "65E6", "ids_1": "⿱日一"},  # ⿱、排除
            "旨": {"unicode": "65E8", "ids_1": "⿱匕日"},  # ⿱、排除
            "昏": {"unicode": "660F", "ids_1": "⿱氏日"},  # ⿱、排除
            "朋": {
                "unicode": "670B",
                "ids_1": "⿰月月",
            },  # 月在 ⿰1 和 ⿰2、含 ⿰2 → 保留
            "朗": {"unicode": "6717", "ids_1": "⿰良月"},
            "期": {"unicode": "671F", "ids_1": "⿰其月"},
            "朣": {"unicode": "6723", "ids_1": "⿰月童"},  # 月在 ⿰1、filter ⿰2 排除
            "萌": {"unicode": "840C", "ids_1": "⿱艹明"},
            # 林 對稱字測試（⿰木木）
            "松": {"unicode": "677E", "ids_1": "⿰木公"},  # 木在 ⿰1
            "梆": {"unicode": "6886", "ids_1": "⿰木邦"},  # 木在 ⿰1
            "沐": {"unicode": "6C90", "ids_1": "⿰氵木"},  # 木在 ⿰2
            # 鐘 嵌套測試
            "鎚": {"unicode": "939A", "ids_1": "⿰金追"},
            "鋩": {"unicode": "92E9", "ids_1": "⿰金芒"},
        }
    )


class TestClassifyByPositionFine:
    """fine 模式：IDC + 位置數字 + is_nested 旗標。

    回傳 (idc, position, is_nested)：
    - position：1/2/3 為單一 match 位置；None 為多位（≡）；對 ∅ 與 〾 一律 None
    - is_nested：False=查詢部件直接是該位置 operand；True=隱在子結構/子字裡
    - 對多位（None）：is_nested = 任一 match 位置是嵌套則 True
    """

    def test_query_direct_left(self, core_position):
        """鐘 = ⿰金童；金在頂層位置 1 直接 → (⿰, 1, False)"""
        assert core_position.classify_by_position("鐘", ["金"], "fine") == (
            "⿰",
            1,
            False,
        )

    def test_query_direct_right(self, core_position):
        """淦 = ⿰氵金；金在頂層位置 2 直接 → (⿰, 2, False)"""
        assert core_position.classify_by_position("淦", ["金"], "fine") == (
            "⿰",
            2,
            False,
        )

    def test_query_symmetric_direct(self, core_position):
        """鍂 = ⿰金金；位置 1 和 2 都直接是金 → (⿰, None, False)（兩位皆直接）"""
        assert core_position.classify_by_position("鍂", ["金"], "fine") == (
            "⿰",
            None,
            False,
        )

    def test_query_symmetric_mixed_direct_and_nested(self, core_position):
        """鑫 = ⿱金鍂；位置 1 直接是金、位置 2 是含金的鍂（嵌套）
        → (⿱, None, True)（混合：一位直接、一位嵌套，is_nested=True）"""
        assert core_position.classify_by_position("鑫", ["金"], "fine") == (
            "⿱",
            None,
            True,
        )

    def test_query_symmetric_all_nested(self, core_position):
        """𨰻 = ⿱⿰金金⿰金金；兩位都是含金的 IDS 子結構 → (⿱, None, True)"""
        assert core_position.classify_by_position("𨰻", ["金"], "fine") == (
            "⿱",
            None,
            True,
        )

    def test_query_in_top_position_2(self, core_position):
        """崟 = ⿱山金；金在頂層位置 2 直接 → (⿱, 2, False)"""
        assert core_position.classify_by_position("崟", ["金"], "fine") == (
            "⿱",
            2,
            False,
        )

    def test_query_in_enclosure(self, core_position):
        """鏖 = ⿸鹿金；金在 ⿸ 位置 2 直接 → (⿸, 2, False)"""
        assert core_position.classify_by_position("鏖", ["金"], "fine") == (
            "⿸",
            2,
            False,
        )

    def test_query_full_enclosure(self, core_position):
        """銜 = ⿴行金；金在 ⿴ 位置 2 直接 → (⿴, 2, False)"""
        assert core_position.classify_by_position("銜", ["金"], "fine") == (
            "⿴",
            2,
            False,
        )

    def test_query_only_in_nested_subcomponent(self, core_position):
        """鐘 中的「立」：鐘=⿰金童、童=⿱立里，立 嵌在童內 → (⿰, 2, True)"""
        assert core_position.classify_by_position("鐘", ["立"], "fine") == (
            "⿰",
            2,
            True,
        )

    def test_query_direct_in_intermediate_char(self, core_position):
        """童 = ⿱立里；立 直接在頂層位置 1 → (⿱, 1, False)"""
        assert core_position.classify_by_position("童", ["立"], "fine") == (
            "⿱",
            1,
            False,
        )

    def test_symmetric_wood(self, core_position):
        """林 = ⿰木木；木對稱、兩位皆直接 → (⿰, None, False)"""
        assert core_position.classify_by_position("林", ["木"], "fine") == (
            "⿰",
            None,
            False,
        )

    def test_nested_symmetric_wood(self, core_position):
        """森 = ⿱木林；位置 1 直接是木、位置 2 是含木的林（嵌套）
        → (⿱, None, True)"""
        assert core_position.classify_by_position("森", ["木"], "fine") == (
            "⿱",
            None,
            True,
        )

    def test_independent_char_returns_empty_label(self, core_position):
        """獨體字（IDS 即自身）→ (∅, None, False)；衍生字流程下不應發生、僅 fallback"""
        assert core_position.classify_by_position("金", ["金"], "fine") == (
            "∅",
            None,
            False,
        )

    def test_query_via_substructure_only(self, core_position):
        """霡 = ⿱雨⿰月永；位置 2 是含永的子結構 ⿰月永（不是永本身）
        → (⿱, 2, True)（單位嵌套）"""
        assert core_position.classify_by_position("霡", ["永"], "fine") == (
            "⿱",
            2,
            True,
        )

    def test_query_via_nested_char_only(self, core_position):
        """𦻑 = ⿱艹詠；位置 2 是含永的子字詠（詠=⿰言永）→ (⿱, 2, True)"""
        assert core_position.classify_by_position("𦻑", ["永"], "fine") == (
            "⿱",
            2,
            True,
        )

    def test_query_direct_position_2(self, core_position):
        """羕 = ⿱𦍌永；永直接是頂層位置 2 → (⿱, 2, False)"""
        assert core_position.classify_by_position("羕", ["永"], "fine") == (
            "⿱",
            2,
            False,
        )


class TestClassifyByPositionCoarse:
    """coarse 模式：只看頂層 IDC、不解析位置；is_nested 對 coarse 標籤無影響、固定回 False。"""

    def test_coarse_drops_position_left(self, core_position):
        """鐘 = ⿰金童；coarse 只回頂層 IDC，不分位置"""
        assert core_position.classify_by_position("鐘", ["金", "童"], "coarse") == (
            "⿰",
            None,
            False,
        )

    def test_coarse_top_idc_only(self, core_position):
        """鑫 = ⿱金鍂；coarse 模式只回 ⿱、不關心對稱與否"""
        assert core_position.classify_by_position("鑫", ["金"], "coarse") == (
            "⿱",
            None,
            False,
        )

    def test_coarse_enclosure(self, core_position):
        """鏖 = ⿸鹿金；coarse 回 ⿸"""
        assert core_position.classify_by_position("鏖", ["金"], "coarse") == (
            "⿸",
            None,
            False,
        )

    def test_coarse_independent_char(self, core_position):
        """獨體字 coarse 也回 ∅"""
        assert core_position.classify_by_position("金", ["金"], "coarse") == (
            "∅",
            None,
            False,
        )


class TestFormatPositionLabel:
    """format_position_label(idc, pos, is_nested)：渲染分組標籤的字面格式。

    is_nested=True 在標籤末加 ·（U+00B7）表「查詢部件嵌在該位置的子結構/子字裡」。
    〾、∅ 無 · 變體（is_nested 對它們不適用）。
    """

    def test_position_1_direct(self, core_position):
        assert core_position.format_position_label("⿰", 1, False) == "⿰1"

    def test_position_1_nested(self, core_position):
        """嵌套位置 1 → ⿰1·"""
        assert core_position.format_position_label("⿰", 1, True) == "⿰1·"

    def test_position_2_direct(self, core_position):
        assert core_position.format_position_label("⿰", 2, False) == "⿰2"

    def test_position_2_nested(self, core_position):
        assert core_position.format_position_label("⿰", 2, True) == "⿰2·"

    def test_position_3(self, core_position):
        """三位結構：⿲ 的位置 3（直接）"""
        assert core_position.format_position_label("⿲", 3, False) == "⿲3"

    def test_multi_position_direct(self, core_position):
        """多位（None）兩位皆直接 → ⿰≡"""
        assert core_position.format_position_label("⿰", None, False) == "⿰≡"

    def test_multi_position_nested(self, core_position):
        """多位含嵌套 → ⿰≡·"""
        assert core_position.format_position_label("⿰", None, True) == "⿰≡·"

    def test_variant_marker_label(self, core_position):
        """〾（變體）無位置數字、無 · 變體"""
        assert core_position.format_position_label("〾", None, False) == "〾"
        assert core_position.format_position_label("〾", None, True) == "〾"

    def test_empty_label_unclassified(self, core_position):
        """∅ fallback 標籤無位置、無 · 變體"""
        assert core_position.format_position_label("∅", None, False) == "∅"
        assert core_position.format_position_label("∅", None, True) == "∅"


class TestGroupByPositionFine:
    """group_by_position（fine）：依位置分組 + 標籤渲染 + 排序的整合行為。

    排序：IDC_ORDER 主序 → 位置升序（1<2<3<None=≡） → 同位置直接優先（False<True 即 ⿰2<⿰2·）。
    每組內字按 Unicode 升序、空組不出現。
    """

    def test_fine_direct_and_nested_split_in_separate_groups(self, core_position):
        """⿰金童 直接位置 vs 子部件嵌套位置應分到不同組。"""
        chars = ["鐘", "淦", "鍂", "鑫", "𨰻", "崟", "鏖", "銜"]
        groups = core_position.group_by_position(chars, ["金"], "fine")
        assert groups == [
            ("⿰1", ["鐘"]),  # 鐘=⿰金童，金 直接在位置 1
            ("⿰2", ["淦"]),  # 淦=⿰氵金，金 直接在位置 2
            ("⿰≡", ["鍂"]),  # 鍂=⿰金金，兩位皆直接
            ("⿱2", ["崟"]),  # 崟=⿱山金，金 直接在位置 2
            ("⿱≡·", ["鑫", "𨰻"]),  # 鑫(混合：1直接+2嵌套)、𨰻(兩位皆嵌套) 都有嵌套
            ("⿴2", ["銜"]),  # 銜=⿴行金
            ("⿸2", ["鏖"]),  # 鏖=⿸鹿金
        ]

    def test_fine_yong_direct_and_nested(self, core_position):
        """搜「永」：羕 直接 vs 霡/𦻑 嵌套需分到 ⿱2 與 ⿱2· 兩組。"""
        chars = ["羕", "霡", "𦻑"]
        groups = core_position.group_by_position(chars, ["永"], "fine")
        assert groups == [
            ("⿱2", ["羕"]),  # 羕=⿱𦍌永，永 直接在位置 2
            (
                "⿱2·",
                ["霡", "𦻑"],
            ),  # 霡=⿱雨⿰月永（永在子結構）、𦻑=⿱艹詠（永在子字）
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


class TestComposeImmediateComponentLines:
    """compose_immediate_component_lines：右欄上半「子部件同位」行組裝。

    對 display_char 頂層 IDS 的每個 operand 位置 N：
    - 若 operand 是單一 Unicode 字 X：列「{format_position_label(IDC, N)} <chars>」
      chars = derived_groups[X] 中、「c 的頂層 IDC == 同 IDC 且位置 N 含 X」的字
    - 若 operand 是 IDS 子結構或 CDP：跳過該位置
    - chars 排序 Unicode 升序、空組不出現
    - 對稱字（如 林=⿰木木）位置 1、2 各自獨立一行
    """

    def test_compound_search_明(self, core_position):
        """搜「明」=⿰日月：⿰1（日同位）+ ⿰2（月同位）；非同位字（⿱結構）排除。"""
        derived = {
            "明": ["萌"],
            "日": ["暗", "暉", "暝", "昂", "昃", "旦", "旨", "昏"],
            "月": ["朋", "朗", "期", "朣"],
        }
        out = core_position.compose_immediate_component_lines(derived, "明")
        # 升序 by ord: 暉(6689) < 暗(6697) < 暝(669D)
        # 朋(670B) < 朗(6717) < 期(671F)；朣(6723)=⿰月童、月在 ⿰1 → 排除
        assert out == [
            ("⿰1", ["暉", "暗", "暝"]),
            ("⿰2", ["朋", "朗", "期"]),
        ]

    def test_leaf_search_金_returns_empty(self, core_position):
        """搜「金」（葉部件、IDS 即自身）：上半無內容。"""
        derived = {"金": ["鐘", "淦", "鍂"]}
        assert core_position.compose_immediate_component_lines(derived, "金") == []

    def test_compound_search_鐘_skips_nested(self, core_position):
        """搜「鐘」=⿰金童：只列 金（⿰1）、童（⿰2）；立/里/田/土 嵌套不列。"""
        derived = {
            "鐘": [],
            "金": ["鎚", "鋩"],
            "童": ["朣"],
            "立": ["拉", "颯"],  # 嵌套、不該出現
            "里": ["野"],
        }
        out = core_position.compose_immediate_component_lines(derived, "鐘")
        # 鋩(92E9) < 鎚(939A) 按 Unicode 升序
        assert out == [
            ("⿰1", ["鋩", "鎚"]),
            ("⿰2", ["朣"]),
        ]

    def test_symmetric_search_林_splits_positions(self, core_position):
        """搜「林」=⿰木木：⿰1 和 ⿰2 各自獨立一行、不合併 ⿰≡。"""
        derived = {"林": ["森"], "木": ["松", "梆", "沐"]}
        out = core_position.compose_immediate_component_lines(derived, "林")
        # 松(677E) < 梆(6886)、木 在 ⿰1 → ⿰1 行
        # 沐(6C90)、木 在 ⿰2 → ⿰2 行
        assert out == [
            ("⿰1", ["松", "梆"]),
            ("⿰2", ["沐"]),
        ]

    def test_substructure_only_𨰻(self, core_position):
        """搜「𨰻」=⿱⿰金金⿰金金：兩位皆子結構非字、上半空。"""
        derived = {"𨰻": []}
        assert core_position.compose_immediate_component_lines(derived, "𨰻") == []

    def test_empty_input(self, core_position):
        assert core_position.compose_immediate_component_lines({}, "明") == []

    def test_independent_char(self, core_position):
        """獨體字（如「金」）：IDS 即自身、上半空。"""
        assert (
            core_position.compose_immediate_component_lines({"金": ["鐘"]}, "金") == []
        )


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
