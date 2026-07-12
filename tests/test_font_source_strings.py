#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字型來源字彙 ↔ localization 鍵護欄（#26）。

font_and_source_for_char 的來源標記以 "font_source_" + source 組 localization
鍵；缺鍵時 L() 靜默退回鍵名字面（tooltip 會顯示 font_source_xxx）。來源字彙
的 canonical 清單在 hanzi_core.FONT_SOURCES、語言清單在 localization.LANGUAGES
——兩端皆 import 而非手抄，新增 tier 或語言時護欄自動擴及。
語言齊備檢查涵蓋「全部」字串鍵，不只 font_source_*（invariant 是全域的）。
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

from hanzi_core import FONT_SOURCES  # noqa: E402
from localization import LANGUAGES, STRINGS  # noqa: E402


class TestFontSourceStrings:
    def test_every_source_has_localization_key(self):
        for source in FONT_SOURCES:
            assert "font_source_" + source in STRINGS, source


class TestAllStringsCoverAllLanguages:
    def test_every_key_covers_every_language(self):
        for key, entry in STRINGS.items():
            for lang in LANGUAGES:
                assert entry.get(lang), (key, lang)
