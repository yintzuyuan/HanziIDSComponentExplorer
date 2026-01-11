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
