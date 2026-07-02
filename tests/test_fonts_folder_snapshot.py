#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fonts_folder_snapshot：參考字型資料夾內容快照純函式（TDD，#26）。

熱更新機制的核心：UI 層列出資料夾的 (檔名, mtime) 交給此函式組快照，
前後快照不相等即代表資料夾有變動 → 清字型快取重新解析。
只納入字型檔（.otf/.ttf/.ttc/.otc，副檔名不分大小寫），忽略隱藏檔與其他檔案；
輸出排序後的 tuple，與輸入順序無關（os.scandir 順序不保證）。
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

from hanzi_core import fonts_folder_snapshot  # noqa: E402


class TestFontsFolderSnapshot:
    def test_empty_folder_gives_empty_snapshot(self):
        assert fonts_folder_snapshot([]) == ()

    def test_filters_non_font_files(self):
        entries = [("MyFont.otf", 1.0), ("readme.txt", 2.0), ("notes.md", 3.0)]
        assert fonts_folder_snapshot(entries) == (("MyFont.otf", 1.0),)

    def test_ignores_hidden_files(self):
        entries = [(".DS_Store", 1.0), (".hidden.otf", 2.0), ("A.otf", 3.0)]
        assert fonts_folder_snapshot(entries) == (("A.otf", 3.0),)

    def test_extension_case_insensitive(self):
        entries = [("A.OTF", 1.0), ("b.TtF", 2.0)]
        assert fonts_folder_snapshot(entries) == (("A.OTF", 1.0), ("b.TtF", 2.0))

    def test_accepts_collection_formats(self):
        entries = [("a.ttc", 1.0), ("b.otc", 2.0)]
        assert fonts_folder_snapshot(entries) == (("a.ttc", 1.0), ("b.otc", 2.0))

    def test_order_independent_of_input_order(self):
        forward = fonts_folder_snapshot([("a.otf", 1.0), ("b.otf", 2.0)])
        backward = fonts_folder_snapshot([("b.otf", 2.0), ("a.otf", 1.0)])
        assert forward == backward

    def test_mtime_change_changes_snapshot(self):
        before = fonts_folder_snapshot([("a.otf", 1.0)])
        after = fonts_folder_snapshot([("a.otf", 2.0)])
        assert before != after

    def test_meta_tuple_size_change_changes_snapshot(self):
        # UI 層傳 (st_mtime_ns, st_size)：mtime 保留式覆蓋（cp -p）靠 size 維度偵測
        before = fonts_folder_snapshot([("a.otf", (100, 2048))])
        after = fonts_folder_snapshot([("a.otf", (100, 4096))])
        assert before != after

    def test_added_file_changes_snapshot(self):
        before = fonts_folder_snapshot([("a.otf", 1.0)])
        after = fonts_folder_snapshot([("a.otf", 1.0), ("b.otf", 1.0)])
        assert before != after
