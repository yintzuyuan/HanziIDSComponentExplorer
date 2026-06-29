#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""font_cache_key：字型快取鍵組成的純函式（TDD，回歸守護）。

背景（#19 回歸）：get_font_for_char 對 last_resort（PUA 造字）的解析已改為依
「當前開啟 Glyphs 文件的家族名」而定，故同一 (char, size) 在不同文件可能應對到
不同字型。原快取鍵僅 (char, size)，會跨文件誤命中，回傳前一文件的陳舊字型
（顯示錯字形或缺字框）。此函式把家族識別納入快取鍵，杜絕跨文件碰撞。

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

from hanzi_core import font_cache_key  # noqa: E402

E000 = chr(0xE000)  # PUA 造字（系統字型必缺，解析依當前文件）
E001 = chr(0xE001)


class TestFontCacheKey:
    """font_cache_key(char, size, font_family) → 可雜湊、含文件身分的快取鍵。"""

    def test_same_inputs_give_equal_keys(self):
        # 同一文件、同字同大小 → 鍵相等（快取命中，避免重複解析）
        assert font_cache_key(E000, 13, "FontA") == font_cache_key(E000, 13, "FontA")

    def test_different_family_gives_distinct_keys(self):
        # 回歸核心：同碼位同大小，但不同文件家族 → 鍵必須不同，
        # 否則文件 A 解析出的 PUA 字型會在文件 B 被誤命中。
        assert font_cache_key(E000, 13, "FontA") != font_cache_key(E000, 13, "FontB")

    def test_different_char_gives_distinct_keys(self):
        assert font_cache_key(E000, 13, "FontA") != font_cache_key(E001, 13, "FontA")

    def test_different_size_gives_distinct_keys(self):
        assert font_cache_key(E000, 13, "FontA") != font_cache_key(E000, 20, "FontA")

    def test_none_and_empty_family_normalize_equal(self):
        # 無開啟文件（None）與空家族名應視為同一狀態，產生穩定且相等的鍵
        assert font_cache_key(E000, 13, None) == font_cache_key(E000, 13, "")

    def test_none_family_distinct_from_named_family(self):
        # 「無文件」與「有具名文件」是不同狀態，不可碰撞
        assert font_cache_key(E000, 13, None) != font_cache_key(E000, 13, "FontA")

    def test_key_is_hashable(self):
        # 必須能當 dict 鍵使用（_font_cache 是 dict）
        cache = {}
        cache[font_cache_key(E000, 13, "FontA")] = "sentinel"
        assert cache[font_cache_key(E000, 13, "FontA")] == "sentinel"

    def test_key_encodes_char_and_size(self):
        # 鍵需可區分 char 與 size（沿用原本以 char+size 為快取維度的語意）
        key = font_cache_key(E000, 13, None)
        assert key != font_cache_key(E000, 14, None)
        assert key != font_cache_key(E001, 13, None)
