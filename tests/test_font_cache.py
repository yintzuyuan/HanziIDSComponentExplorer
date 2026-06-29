#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FontCache：get_font_for_char 的字型快取純邏輯（TDD，效能回歸守護）。

背景（健檢 #1）：某 PUA 碼位無任何已安裝字型涵蓋時，_resolve_glyph_font 回 None，
原 get_font_for_char 在此路徑「不寫快取」直接回系統字型。後果：中欄 cell 每次
捲動／選取／focus 重繪都重跑 _brute_force_covering_font 全字型暴力掃描 → 卡頓。

修法是「負向快取」：記住此鍵已知無涵蓋字型，重繪時直接命中、不再重掃；負向項
視為暫時性（使用者可能稍後安裝字型），故 forget_missing 於新搜尋時清掉以重試，
正向項（家族已納入鍵、永久有效）則保留不動。

font 值在純測試中以不透明 sentinel 表達，不需 AppKit。
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

from hanzi_core import FontCache  # noqa: E402

KEY_A = (chr(0xE000), 13, "FontA")
KEY_B = (chr(0xE001), 13, "FontA")
FONT = object()  # 不透明字型物件替身


class TestLookupStates:
    """lookup(key) → (state, font)：'hit' / 'missing'（已知無涵蓋）/ 'miss'（未知）。"""

    def test_unknown_key_is_miss(self):
        cache = FontCache()
        assert cache.lookup(KEY_A) == ("miss", None)

    def test_hit_after_store(self):
        cache = FontCache()
        cache.store(KEY_A, FONT)
        assert cache.lookup(KEY_A) == ("hit", FONT)

    def test_missing_after_store_missing(self):
        # 回歸核心：負向結果必須被記住，否則每次重繪都重跑暴力掃描
        cache = FontCache()
        cache.store_missing(KEY_A)
        assert cache.lookup(KEY_A) == ("missing", None)

    def test_positive_and_negative_coexist(self):
        cache = FontCache()
        cache.store(KEY_A, FONT)
        cache.store_missing(KEY_B)
        assert cache.lookup(KEY_A) == ("hit", FONT)
        assert cache.lookup(KEY_B) == ("missing", None)


class TestForgetMissing:
    """forget_missing()：清負向項以重試（裝字型後），保留正向項。"""

    def test_forget_missing_drops_negatives(self):
        cache = FontCache()
        cache.store_missing(KEY_A)
        cache.forget_missing()
        # 負向項已清 → 變回 miss，下次會重新解析（可能命中新裝字型）
        assert cache.lookup(KEY_A) == ("miss", None)

    def test_forget_missing_keeps_positives(self):
        cache = FontCache()
        cache.store(KEY_A, FONT)
        cache.store_missing(KEY_B)
        cache.forget_missing()
        assert cache.lookup(KEY_A) == ("hit", FONT)
        assert cache.lookup(KEY_B) == ("miss", None)


class TestClear:
    def test_clear_removes_everything(self):
        cache = FontCache()
        cache.store(KEY_A, FONT)
        cache.store_missing(KEY_B)
        cache.clear()
        assert cache.lookup(KEY_A) == ("miss", None)
        assert cache.lookup(KEY_B) == ("miss", None)


class TestEviction:
    """超過上限時驅逐前半（沿用原 get_font_for_char 的容量管理語意）。"""

    def test_evicts_when_exceeding_max(self):
        cache = FontCache(max_size=4)
        for i in range(5):
            cache.store((chr(0xE000 + i), 13, "F"), object())
        # 第 5 筆寫入前 len 已達上限 → 驅逐前半（最舊 2 筆）
        assert cache.lookup((chr(0xE000), 13, "F"))[0] == "miss"
        # 最新寫入仍在
        assert cache.lookup((chr(0xE004), 13, "F"))[0] == "hit"

    def test_missing_entries_count_toward_eviction(self):
        # 負向項也占容量，必須一併納入驅逐，避免無上限成長
        cache = FontCache(max_size=4)
        for i in range(5):
            cache.store_missing((chr(0xF000 + i), 13, "F"))
        # 最舊負向項被驅逐 → miss；最新負向項仍記得 → missing
        assert cache.lookup((chr(0xF000), 13, "F"))[0] == "miss"
        assert cache.lookup((chr(0xF004), 13, "F")) == ("missing", None)
