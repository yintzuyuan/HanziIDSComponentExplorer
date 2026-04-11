#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IDS Generator 測試套件

安全說明：此專案使用 gzip+pickle 格式是為了與現有 Glyphs 外掛相容。
pickle 序列化僅用於本地生成的受信任資料。
"""

import gzip
import pickle
import sys
from pathlib import Path

import pytest

# 將 scripts 加入路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ids_generator import IDSGenerator


# 跳過條件：資料來源不存在時跳過整合測試
DATA_EXISTS = Path("data/chise-ids").exists()
skip_if_no_data = pytest.mark.skipif(
    not DATA_EXISTS,
    reason="資料來源不存在，請執行 python scripts/build_ids.py --download",
)


class TestIDSGeneratorInit:
    """測試 IDSGenerator 初始化"""

    def test_init_creates_output_dir(self, tmp_path):
        """測試初始化時建立輸出目錄"""
        dist_path = tmp_path / "dist"

        IDSGenerator(
            chise_ids_path=tmp_path / "chise-ids",
            unicode_mapping_path=tmp_path / "cns",
            dist_path=dist_path,
        )

        assert dist_path.exists()


@skip_if_no_data
class TestLoadIDSFiles:
    """測試載入 IDS 檔案"""

    @pytest.fixture
    def generator(self):
        return IDSGenerator()

    def test_load_ucs_files_exist(self, generator):
        """測試 UCS 檔案存在"""
        ucs_files = list(generator.chise_ids_path.glob("IDS-UCS-*.txt"))
        assert len(ucs_files) > 0, "應該找到 UCS 檔案"

    def test_load_ids_data(self, generator):
        """測試載入 IDS 資料"""
        ids_data = generator._load_ids_files()
        assert len(ids_data) > 0, "應該載入 IDS 資料"
        assert len(ids_data) > 90000, f"字符數量應超過 90000，實際：{len(ids_data)}"


@skip_if_no_data
class TestIDSDataStructure:
    """測試 IDS 資料結構"""

    @pytest.fixture
    def generator(self):
        return IDSGenerator()

    def test_ids_record_structure(self, generator):
        """測試 IDS 記錄結構"""
        ids_data = generator._load_ids_files()
        _, sample_record = next(iter(ids_data.items()))

        assert "character" in sample_record
        assert "unicode" in sample_record
        assert "ids_1" in sample_record
        assert "ids_2" in sample_record

    def test_multiple_ids_expressions(self, generator):
        """測試多拆法支援"""
        ids_data = generator._load_ids_files()
        records_with_ids_2 = sum(
            1 for record in ids_data.values() if record.get("ids_2")
        )
        assert records_with_ids_2 > 0, "應該有字符具有多種拆法"


@skip_if_no_data
class TestBuild:
    """測試建置流程"""

    @pytest.fixture
    def generator(self, tmp_path):
        return IDSGenerator(dist_path=tmp_path / "dist")

    def test_build_creates_pdata(self, generator):
        """測試建置產生 pdata 檔案"""
        pdata_path = generator.build()

        assert pdata_path.exists()
        assert pdata_path.suffix == ".pdata"

    def test_pdata_loadable(self, generator):
        """測試 pdata 可載入"""
        pdata_path = generator.build()

        with gzip.open(pdata_path, "rb") as f:
            data = pickle.load(f)

        assert len(data) > 90000

    def test_pdata_structure(self, generator):
        """測試 pdata 資料結構"""
        pdata_path = generator.build()

        with gzip.open(pdata_path, "rb") as f:
            data = pickle.load(f)

        sample_char, sample_data = next(iter(data.items()))

        assert isinstance(sample_char, str)
        assert "unicode" in sample_data
        assert "ids_1" in sample_data
        assert "ids_2" in sample_data


class TestStrokeDataLoading:
    """測試從 CNS_stroke.txt 載入筆畫資料"""

    def test_load_stroke_data_returns_empty_when_file_missing(self, tmp_path):
        """檔案不存在時應回傳空 dict 並印警告，不應拋例外"""
        generator = IDSGenerator(
            chise_ids_path=tmp_path / "chise-ids",
            unicode_mapping_path=tmp_path / "cns_mapping",
            cns_properties_path=tmp_path / "cns_properties",  # 不存在
            dist_path=tmp_path / "dist",
        )

        stroke_map = generator._load_stroke_data()
        assert stroke_map == {}

    def test_load_stroke_data_parses_real_format(self, tmp_path):
        """測試解析 CNS_stroke.txt 真實格式：cns_code\\tstroke_count"""
        # 準備假的 CNS properties 目錄
        cns_props = tmp_path / "cns_properties"
        cns_props.mkdir()
        stroke_file = cns_props / "CNS_stroke.txt"
        stroke_file.write_text(
            "1-2122\t1\n1-4421\t6\n2-2433\t10\n",
            encoding="utf-8",
        )

        # 準備假的 CNS→Unicode mapping
        cns_mapping = tmp_path / "cns_mapping"
        cns_mapping.mkdir()
        mapping_file = cns_mapping / "CNS2UNICODE_Unicode_BMP.txt"
        mapping_file.write_text(
            "1-2122\t4E00\n1-4421\t5B57\n2-2433\t6F22\n",
            encoding="utf-8",
        )

        generator = IDSGenerator(
            chise_ids_path=tmp_path / "chise-ids",
            unicode_mapping_path=cns_mapping,
            cns_properties_path=cns_props,
            dist_path=tmp_path / "dist",
        )

        stroke_map = generator._load_stroke_data()

        assert stroke_map == {
            "4E00": 1,
            "5B57": 6,
            "6F22": 10,
        }

    def test_load_stroke_data_skips_unmapped_cns_codes(self, tmp_path):
        """無 CNS→Unicode 對應的 CNS 碼應被跳過，不阻擋其他資料"""
        cns_props = tmp_path / "cns_properties"
        cns_props.mkdir()
        (cns_props / "CNS_stroke.txt").write_text(
            "1-2122\t1\n99-9999\t99\n",  # 99-9999 沒有 mapping
            encoding="utf-8",
        )

        cns_mapping = tmp_path / "cns_mapping"
        cns_mapping.mkdir()
        (cns_mapping / "CNS2UNICODE_Unicode_BMP.txt").write_text(
            "1-2122\t4E00\n",
            encoding="utf-8",
        )

        generator = IDSGenerator(
            chise_ids_path=tmp_path / "chise-ids",
            unicode_mapping_path=cns_mapping,
            cns_properties_path=cns_props,
            dist_path=tmp_path / "dist",
        )

        stroke_map = generator._load_stroke_data()
        assert stroke_map == {"4E00": 1}
        assert "99-9999" not in stroke_map


@skip_if_no_data
class TestStrokeDataIntegration:
    """測試 strokes 欄位整合到最終資料庫

    透過 HanziCore 載入剛建置的 pdata，避免測試直接處理底層格式。
    """

    @pytest.fixture
    def built_core(self, tmp_path):
        """建置一個新 pdata 並用 HanziCore 載入"""
        # 動態 import 避免在 collect 階段就要求 Resources 存在
        plugin_resources = (
            Path(__file__).parent.parent
            / "HanziIDSComponentExplorer.glyphsPlugin"
            / "Contents"
            / "Resources"
        )
        sys.path.insert(0, str(plugin_resources))
        from hanzi_core import HanziCore

        generator = IDSGenerator(dist_path=tmp_path / "dist")
        pdata_path = generator.build()
        return HanziCore(str(pdata_path))

    def test_known_char_has_correct_stroke_count(self, built_core):
        """「字」應為 6 畫（CNS 標準）"""
        strokes = built_core.get_stroke_count("字")
        assert strokes == 6, f"「字」應為 6 畫，實際：{strokes}"

    def test_multiple_known_chars(self, built_core):
        """抽樣多個常見字，確認筆畫資料正確"""
        # CNS 標準筆畫數
        expected = {
            "一": 1,
            "二": 2,
            "三": 3,
            "木": 4,
            "字": 6,
        }
        for char, expected_strokes in expected.items():
            actual = built_core.get_stroke_count(char)
            assert actual == expected_strokes, (
                f"「{char}」應為 {expected_strokes} 畫，實際：{actual}"
            )

    def test_database_has_meaningful_stroke_coverage(self, built_core):
        """資料庫應有大量字具有 strokes，少量字 strokes 為 None"""
        int_count = 0
        none_count = 0
        for char in built_core.db:
            strokes = built_core.get_stroke_count(char)
            if strokes is None:
                none_count += 1
            else:
                int_count += 1

        assert int_count > 50000, f"應有大量字含 strokes，實際：{int_count}"
        # 至少有一些超出 CNS 範圍的字（Ext-G/H 等）
        assert none_count > 0, "應有部分字 strokes 為 None"


@skip_if_no_data
class TestOutputConsistency:
    """測試與現有 pdata 一致性"""

    def test_compare_with_existing(self, tmp_path):
        """測試與現有 pdata 一致性"""
        existing_pdata = Path(
            "HanziIDSComponentExplorer.glyphsPlugin/Contents/Resources/data/ids.pdata"
        )

        if not existing_pdata.exists():
            pytest.skip("現有 pdata 不存在")

        # 載入現有資料
        with gzip.open(existing_pdata, "rb") as f:
            existing_data = pickle.load(f)

        # 建置新資料
        generator = IDSGenerator(dist_path=tmp_path / "dist")
        new_pdata = generator.build()

        with gzip.open(new_pdata, "rb") as f:
            new_data = pickle.load(f)

        # 比較字符數量（允許較大差異，上游會持續更新）
        diff = abs(len(new_data) - len(existing_data))
        assert diff < 10000, f"字符數量差異過大：{diff}"

        # 驗證常見字符
        test_chars = ["木", "林", "森", "漢", "字"]
        for char in test_chars:
            if char in existing_data and char in new_data:
                assert new_data[char]["unicode"] == existing_data[char]["unicode"]
