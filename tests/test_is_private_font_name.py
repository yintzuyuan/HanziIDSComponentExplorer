#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""is_private_font_name：系統私有字型家族名判定純函式（TDD，#26）。

Apple 內部字型家族名以 '.' 開頭（.AppleSystemUIFont、.SF NS 等），只有系統
cascade 找得到、不應洩漏給使用者。預覽 tooltip 以此在 cascade 命中隱藏系統
字型時改用通用名，避免洩漏私有名（PR #28 review ③；先前僅 'system' 來源有防護）。
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

from hanzi_core import is_private_font_name  # noqa: E402


class TestIsPrivateFontName:
    def test_apple_system_ui_font_is_private(self):
        assert is_private_font_name(".AppleSystemUIFont")

    def test_sf_ns_is_private(self):
        assert is_private_font_name(".SF NS")

    def test_dot_prefixed_is_private(self):
        assert is_private_font_name(".LastResort")

    def test_visible_family_is_not_private(self):
        assert not is_private_font_name("Songti SC")

    def test_none_is_not_private(self):
        assert not is_private_font_name(None)

    def test_empty_is_not_private(self):
        assert not is_private_font_name("")
