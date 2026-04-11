#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IDS 資料庫生成器

從 CHISE IDS 資料來源直接生成 ids.pdata 檔案。
資料來源由 CI/CD 動態下載，不進版控。

安全說明：此專案使用 gzip+pickle 格式是為了與現有 Glyphs 外掛相容。
pickle 序列化僅用於本地生成的受信任資料，資料來源為官方 CHISE IDS。
"""

import gzip
import os
import pickle
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv


class IDSGenerator:
    """IDS 資料庫生成器 - 直接從 CHISE IDS 轉換為 pdata 格式"""

    def __init__(
        self,
        chise_ids_path: Optional[Path] = None,
        unicode_mapping_path: Optional[Path] = None,
        cns_properties_path: Optional[Path] = None,
        dist_path: Optional[Path] = None,
    ):
        load_dotenv()

        self.chise_ids_path = chise_ids_path or Path(
            os.getenv("DATA_CHISE_IDS_PATH", "./data/chise-ids")
        )
        self.unicode_mapping_path = unicode_mapping_path or Path(
            os.getenv(
                "UNICODE_MAPPING_PATH",
                "./data/cns11643/Tables/MapingTables/Unicode",
            )
        )
        self.cns_properties_path = cns_properties_path or Path(
            os.getenv(
                "CNS_PROPERTIES_PATH",
                "./data/cns11643/Tables/Properties",
            )
        )
        self.dist_path = dist_path or Path(os.getenv("DIST_PATH", "./dist"))

        # 確保輸出目錄存在
        self.dist_path.mkdir(parents=True, exist_ok=True)

    def build(self) -> Path:
        """完整建置流程，回傳 ids.pdata 路徑"""
        print("載入 IDS 資料...")
        ids_data = self._load_ids_files()
        print(f"  載入 {len(ids_data)} 個字符")

        print("載入筆畫資料...")
        stroke_map = self._load_stroke_data()
        print(f"  載入 {len(stroke_map)} 筆筆畫資料")

        print("轉換為 pdata 格式...")
        pdata_path = self._save_pdata(ids_data, stroke_map)
        print(f"  輸出：{pdata_path}")

        return pdata_path

    def _load_ids_files(self) -> Dict[str, Dict]:
        """載入所有 IDS 檔案並回傳處理後的資料"""
        ids_data: Dict[str, Dict] = {}

        # 載入 UCS 檔案
        ucs_files = list(self.chise_ids_path.glob("IDS-UCS-*.txt"))
        self._process_ucs_files(ucs_files, ids_data)

        # 載入 CNS 檔案（需要 CNS 到 Unicode 映射）
        cns_files = list(self.chise_ids_path.glob("IDS-CNS-*.txt"))
        if cns_files and self.unicode_mapping_path.exists():
            self._process_cns_files(cns_files, ids_data)

        return ids_data

    def _process_ucs_files(
        self, ucs_files: list[Path], ids_data: Dict[str, Dict]
    ) -> None:
        """處理 UCS 格式的 IDS 檔案"""
        for file_path in ucs_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()

                        # 跳過註釋行
                        if line.startswith(";") or line.startswith("#") or not line:
                            continue

                        # 解析格式：U+XXXX<tab>字符<tab>IDS 或 U-XXXXXXXX<tab>字符<tab>IDS
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            unicode_part = parts[0]
                            character = parts[1]
                            ids_expression = parts[2]

                            # 提取 Unicode 值
                            unicode_val = None
                            if unicode_part.startswith("U+"):
                                unicode_val = unicode_part[2:].upper()
                            elif unicode_part.startswith("U-"):
                                unicode_val = unicode_part[2:].upper()

                            if unicode_val and ids_expression:
                                self._add_ids_record(
                                    ids_data, unicode_val, character, ids_expression
                                )

            except Exception as e:
                print(f"警告：無法讀取 {file_path}: {e}")

    def _process_cns_files(
        self, cns_files: list[Path], ids_data: Dict[str, Dict]
    ) -> None:
        """處理 CNS 格式的 IDS 檔案"""
        cns_to_unicode = self._load_cns_to_unicode_mapping()

        for file_path in cns_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()

                        if line.startswith(";") or line.startswith("#") or not line:
                            continue

                        parts = line.split("\t")
                        if len(parts) >= 3:
                            cns_code = parts[0]
                            character = parts[1]
                            ids_expression = parts[2]

                            if ids_expression:
                                unicode_val = cns_to_unicode.get(cns_code)
                                if unicode_val:
                                    actual_char = self._extract_character(character)
                                    self._add_ids_record(
                                        ids_data,
                                        unicode_val,
                                        actual_char,
                                        ids_expression,
                                    )

            except Exception as e:
                print(f"警告：無法讀取 {file_path}: {e}")

    def _load_stroke_data(self) -> Dict[str, int]:
        """從 CNS_stroke.txt 載入筆畫資料

        資料來源：CNS11643-OpenData 的 Tables/Properties/CNS_stroke.txt
        格式：cns_code\\tstroke_count（例：1-2122\\t1）

        透過 _load_cns_to_unicode_mapping() 把 CNS 碼轉成 Unicode 十六進位字串。

        回傳:
            Dict[str, int]: {unicode_hex: stroke_count}
            檔案不存在或無對應 mapping 時為空 dict。
        """
        stroke_file = self.cns_properties_path / "CNS_stroke.txt"

        if not stroke_file.exists():
            print(f"警告：找不到筆畫資料檔 {stroke_file}，外掛將無筆畫篩選功能")
            return {}

        # 取得 CNS→Unicode 對應（重用既有邏輯）
        cns_to_unicode = self._load_cns_to_unicode_mapping()
        if not cns_to_unicode:
            print("警告：CNS→Unicode mapping 為空，無法解析筆畫資料")
            return {}

        stroke_map: Dict[str, int] = {}
        try:
            with open(stroke_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split("\t")
                    if len(parts) < 2:
                        continue

                    cns_code = parts[0]
                    try:
                        stroke_count = int(parts[1])
                    except ValueError:
                        continue

                    # 正規化 CNS 格式：3-2144 → C3-2144（與 mapping 一致）
                    if "-" in cns_code:
                        plane, code = cns_code.split("-", 1)
                        normalized = f"C{plane}-{code}"
                        unicode_hex = cns_to_unicode.get(normalized)
                        if unicode_hex:
                            stroke_map[unicode_hex.upper()] = stroke_count

        except Exception as e:
            print(f"警告：讀取筆畫資料時出錯：{e}")
            return {}

        return stroke_map

    def _load_cns_to_unicode_mapping(self) -> Dict[str, str]:
        """載入 CNS 到 Unicode 的映射"""
        mapping: Dict[str, str] = {}

        for file_path in self.unicode_mapping_path.glob("CNS2UNICODE_*.txt"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and "\t" in line:
                            parts = line.split("\t")
                            if len(parts) >= 2:
                                cns_code = parts[0]
                                unicode_hex = parts[1]
                                # 正規化 CNS 格式：3-2144 -> C3-2144
                                if "-" in cns_code:
                                    plane, code = cns_code.split("-", 1)
                                    normalized = f"C{plane}-{code}"
                                    mapping[normalized] = unicode_hex.upper()
            except Exception as e:
                print(f"警告：無法讀取 {file_path}: {e}")

        return mapping

    def _add_ids_record(
        self,
        ids_data: Dict[str, Dict],
        unicode_val: str,
        character: str,
        ids_expression: str,
    ) -> None:
        """新增或更新 IDS 記錄"""
        if unicode_val not in ids_data:
            ids_data[unicode_val] = {
                "character": character,
                "unicode": unicode_val,
                "ids_1": None,
                "ids_2": None,
            }

        # 分配 IDS 到 ids_1 或 ids_2，避免重複
        record = ids_data[unicode_val]
        if record["ids_1"] is None:
            record["ids_1"] = ids_expression
        elif record["ids_2"] is None and ids_expression != record["ids_1"]:
            record["ids_2"] = ids_expression

    def _extract_character(self, character_part: str) -> str:
        """從 CNS 行中提取實際字符"""
        if "&I-" in character_part and ";" in character_part:
            parts = character_part.split(";")
            if len(parts) > 1 and parts[1]:
                return parts[1]
        return character_part

    def _save_pdata(
        self,
        ids_data: Dict[str, Dict],
        stroke_map: Optional[Dict[str, int]] = None,
    ) -> Path:
        """將資料儲存為 gzip 壓縮的序列化格式（與現有外掛相容）

        參數:
            ids_data: 從 _load_ids_files 取得的 IDS 資料
            stroke_map: 從 _load_stroke_data 取得的 {unicode_hex: stroke_count}
                        若為 None 或空 dict，所有紀錄的 strokes 為 None
        """
        stroke_map = stroke_map or {}

        # 正規化 stroke_map 的 key 為「無前導零」形式，以便與 IDS 的兩種 unicode
        # 表示法（U+4E00 / U-00020000）統一比對：
        # - BMP："4E00" → "4E00"
        # - 非 BMP："00020000"（CHISE 格式） / "20000"（CNS 格式）→ 都正規化為 "20000"
        normalized_stroke_map: Dict[str, int] = {
            key.lstrip("0") or "0": value for key, value in stroke_map.items()
        }

        def _lookup_strokes(unicode_val: str) -> Optional[int]:
            if not unicode_val:
                return None
            normalized = unicode_val.lstrip("0") or "0"
            return normalized_stroke_map.get(normalized)

        # 轉換為以字符為 key 的格式
        output_data: Dict[str, Dict] = {}
        for record in ids_data.values():
            char = record["character"]
            output_data[char] = {
                "unicode": record["unicode"],
                "ids_1": record["ids_1"],
                "ids_2": record["ids_2"],
                "strokes": _lookup_strokes(record["unicode"]),
            }

        pdata_path = self.dist_path / "ids.pdata"
        with gzip.open(pdata_path, "wb", compresslevel=6) as f:
            pickle.dump(output_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        return pdata_path


if __name__ == "__main__":
    generator = IDSGenerator()
    generator.build()
