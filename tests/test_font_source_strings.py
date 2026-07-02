#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字型來源字彙 ↔ localization 鍵護欄（#26）。

font_and_source_for_char 的來源標記以 "font_source_" + source 組 localization
鍵；缺鍵時 L() 靜默退回鍵名字面（tooltip 會顯示 font_source_xxx）。此測試
鎖住每個來源都有對應字串鍵、且四種語言齊備——新增 tier 時忘加字串會在此爆。
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

from localization import STRINGS  # noqa: E402

# font_and_source_for_char（glyphs_ui.py）回傳的全部來源標記
FONT_SOURCES = ("folder", "family", "covering", "cascade", "system")
LANGUAGES = ("en", "zh-Hant", "zh-Hans", "ja")


class TestFontSourceStrings:
    def test_every_source_has_localization_key(self):
        for source in FONT_SOURCES:
            assert "font_source_" + source in STRINGS, source

    def test_every_source_string_covers_all_languages(self):
        for source in FONT_SOURCES:
            entry = STRINGS["font_source_" + source]
            for lang in LANGUAGES:
                assert entry.get(lang), (source, lang)
