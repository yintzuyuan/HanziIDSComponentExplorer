#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hanzi Component Explorer - 核心邏輯層
完全獨立的漢字分析引擎，無任何 UI 或 Glyphs 依賴

© 2025 TzuYuan Yin
"""

from __future__ import division, print_function, unicode_literals

import re
import os
import gzip
import pickle
from typing import Dict, List, Tuple, Union, Optional, Set
from pathlib import Path


# 錯誤訊息常數定義
ERROR_NO_MATCH_FOUND = "未找到符合的字符"
ERROR_UNKNOWN_CHAR = "未知字符"
ERROR_SEARCH_FAILED = "搜尋失敗"

# IDS 分隔字符 (Ideographic Description Characters)
IDC_CHARS = '⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻〾'


class HanziCore:
    """漢字部件分析核心引擎"""

    def __init__(self, data_path: str):
        """
        初始化引擎並載入資料庫

        參數:
        data_path (str): IDS 資料庫檔案路徑（.pdata 格式）
        """
        self.data_path = self._resolve_path(data_path)
        self.db = self._load_database()

    def _resolve_path(self, path: str) -> Path:
        """
        解析資料庫路徑

        參數:
        path (str): 資料庫路徑（可以是相對或絕對路徑）

        回傳:
        Path: 解析後的絕對路徑
        """
        path_obj = Path(path)

        if not path_obj.is_absolute():
            # 相對路徑：相對於當前檔案所在目錄
            script_dir = Path(__file__).parent
            path_obj = script_dir / path_obj

        if not path_obj.exists():
            raise FileNotFoundError(f"資料庫檔案不存在：{path_obj}")

        return path_obj

    def _load_database(self) -> Dict[str, Dict[str, str]]:
        """
        載入 gzip+pickle 格式的漢字資料庫

        回傳:
        Dict[str, Dict[str, str]]: 漢字資料庫
            格式: {'字符': {'unicode': 'xxxx', 'char': '字符', 'ids_1': 'xxx', 'ids_2': 'xxx'}}
        """
        try:
            with gzip.open(str(self.data_path), 'rb') as f:
                pdata = pickle.load(f)

            if not isinstance(pdata, dict):
                raise ValueError(f"資料庫格式錯誤，期望字典，取得 {type(pdata)}")

            # 轉換為內部格式
            return self._convert_format(pdata)

        except gzip.BadGzipFile:
            raise ValueError(f"無效的 gzip 檔案: {self.data_path}")
        except pickle.UnpicklingError:
            raise ValueError(f"pickle 反序列化失敗: {self.data_path}")
        except Exception as e:
            raise RuntimeError(f"資料庫載入失敗: {e}")

    def _convert_format(self, pdata: Dict[str, Dict[str, Optional[str]]]) -> Dict[str, Dict[str, str]]:
        """
        將新格式資料庫轉換為內部使用格式，保留所有 IDS 變體

        參數:
        pdata: 新格式資料庫

        回傳:
        內部格式資料庫
            格式: {'字符': {'unicode': 'xxxx', 'char': '字符', 'ids_1': 'xxx', 'ids_2': 'xxx'}}
        """
        converted_data = {}

        for char, data in pdata.items():
            converted_data[char] = {
                'unicode': data.get('unicode', ''),
                'char': char,
                'ids_1': data.get('ids_1', ''),
                'ids_2': data.get('ids_2', '')
            }

        return converted_data

    # === 字符查詢 ===

    def get_data(self, char_or_code: str) -> Dict[str, Dict[str, str]]:
        """
        獲取字符的相關資料，支援 Unicode 編碼

        參數:
        char_or_code (str): 漢字或 Unicode 編碼（支援 U+4E00, uni4E00, 4E00 等格式）
                           當輸入多個字符時，自動取第一個有效字符

        回傳:
        Dict[str, Dict[str, str]]: 包含字符資料的字典
        """
        # 處理多字符輸入：逐個嘗試，返回第一個有效字符
        # 排除 Unicode 格式（U+、uni、u 前綴）和純十六進位值
        is_unicode_format = (
            char_or_code.startswith(('U+', 'uni', 'u')) or
            (len(char_or_code) in (4, 5) and all(c in '0123456789ABCDEFabcdef' for c in char_or_code))
        )
        if len(char_or_code) > 1 and not is_unicode_format:
            for char in char_or_code:
                if char.strip() and char in self.db:
                    return {char: self.db[char]}
            # 所有字符都無效
            return {}

        # 直接字符查詢
        if char_or_code in self.db:
            return {char_or_code: self.db[char_or_code]}

        # Unicode 格式標準化處理
        normalized_code = char_or_code.upper()
        if normalized_code.startswith(('U+', 'UNI')):
            # 移除 U+ 或 UNI 前綴
            normalized_code = normalized_code.replace('U+', '').replace('UNI', '')
        elif normalized_code.startswith('U'):
            # 處理只有 u 前綴的情況
            normalized_code = normalized_code[1:]

        # 在資料庫中搜尋匹配的 Unicode
        for char, data in self.db.items():
            if 'unicode' in data and data['unicode'].upper() == normalized_code:
                return {char: data}

        return {}

    def parse_ids(self, ids: Union[str, List[str]]) -> List[List[str]]:
        """
        解析 IDS（Ideographic Description Sequence）字符串

        參數:
        ids (str 或 List[str]): IDS 字符串或 IDS 字符串列表

        回傳:
        List[List[str]]: 解析後的 IDS 列表
        """
        def split_special_chars(s):
            return re.findall(r'&[^;]+;|[⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻〾]|\S', s)

        if isinstance(ids, list):
            return [split_special_chars(id_str) for id_str in ids]
        else:
            return [split_special_chars(ids)]

    # === 搜尋功能 ===

    def search(self, query: str, charset: Optional[Set[str]] = None) -> List[str]:
        """
        根據部件搜尋相關字符，支援模糊搜尋

        參數:
        query (str): 要搜尋的部件或字符
        charset (Optional[Set[str]]): 可選的字符集篩選（None = 搜尋全部）

        回傳:
        List[str]: 包含該部件的字符列表
        """
        results = []
        query_lower = query.lower()

        for char, data in self.db.items():
            found = False

            # 1. 檢查字符本身
            if query_lower in char.lower():
                found = True

            # 2. 檢查 Unicode（轉為字符比對）
            elif query_lower in data.get('unicode', '').lower():
                found = True

            # 3. 檢查 IDS 結構中的部件（檢查所有變體）
            elif data.get('ids_1') or data.get('ids_2'):
                try:
                    # 收集所有 IDS 變體
                    ids_variants = []
                    if data.get('ids_1'):
                        ids_variants.append(data['ids_1'])
                    if data.get('ids_2'):
                        ids_variants.append(data['ids_2'])

                    # 在所有變體中搜尋
                    for ids in ids_variants:
                        parsed_ids_list = self.parse_ids(ids)
                        for ids_sequence in parsed_ids_list:
                            for ids_part in ids_sequence:
                                if query_lower == ids_part.lower():
                                    found = True
                                    break
                            if found:
                                break
                        if found:
                            break
                except Exception:
                    # 如果解析失敗，退回到字串搜尋
                    for ids in ids_variants:
                        if query_lower in ids.lower():
                            found = True
                            break

            if found:
                results.append(char)

        # 套用字符集篩選
        if charset is not None:
            results = [c for c in results if c in charset]

        return results

    def find_sister_characters(self, char: str, charset: Optional[Set[str]] = None, variant_index: int = 0) -> Dict[str, Dict[str, List[str]]]:
        """
        搜尋同字根，根據結構和部件相似度分級，排除獨體字

        參數:
        char (str): 要搜尋同字根的字符
        charset (Optional[Set[str]]): 可選的字符集篩選
        variant_index (int): 使用第幾種拆法（0=ids_1, 1=ids_2, -1=合併所有）

        回傳:
        Dict[str, Dict[str, List[str]]]: 同字根資料
            格式: {'結構相同部件同位': {'木': ['林', '森']}, ...}
        """
        target_data = self.db.get(char)
        if not target_data:
            return {}

        # 如果是 variant_index == -1，合併所有拆法的結果
        if variant_index == -1:
            result_1 = self._find_sister_by_ids(char, target_data.get('ids_1', ''), charset)
            result_2 = self._find_sister_by_ids(char, target_data.get('ids_2', ''), charset)
            return self._merge_sister_results(result_1, result_2)

        # 根據 variant_index 選擇 IDS
        if variant_index == 0:
            target_ids = target_data.get('ids_1') or target_data.get('ids_2', '')
        elif variant_index == 1:
            target_ids = target_data.get('ids_2') or target_data.get('ids_1', '')
        else:
            target_ids = target_data.get('ids_1') or target_data.get('ids_2', '')

        if not target_ids:
            return {}

        return self._find_sister_by_ids(char, target_ids, charset)

    def _find_sister_by_ids(self, char: str, target_ids: str, charset: Optional[Set[str]] = None) -> Dict[str, Dict[str, List[str]]]:
        """
        根據指定的 IDS 搜尋同字根（內部方法）
        """
        if not target_ids:
            return {}

        target_structure = ''.join([c for c in target_ids if c in IDC_CHARS])
        target_components = [c for c in self.parse_ids(target_ids)[0] if c not in IDC_CHARS]

        # 檢查是否為獨體字
        if len(target_components) <= 1:
            return {
                "獨體字": {
                    char: [char]
                }
            }

        sisters = {
            "結構相同部件同位": {},
            "結構部件相同": {},
            "部件相同": {}
        }

        for c, data in self.db.items():
            if c == char:
                continue

            # 套用字符集篩選（提前過濾）
            if charset is not None and c not in charset:
                continue

            # 收集所有 IDS 變體
            ids_variants = []
            if data.get('ids_1'):
                ids_variants.append(data['ids_1'])
            if data.get('ids_2'):
                ids_variants.append(data['ids_2'])

            if not ids_variants:
                continue

            # 遍歷所有拆法,找到匹配後停止(避免同一字符重複加入)
            found_sister = False
            for ids in ids_variants:
                if found_sister:
                    break

                structure = ''.join([c for c in ids if c in IDC_CHARS])
                components = [c for c in self.parse_ids(ids)[0] if c not in IDC_CHARS]

                # 排除獨體字
                if len(components) == 1:
                    continue

                if structure == target_structure:
                    # 檢查每個位置的部件是否相同
                    same_position_components = []
                    for i, (target_comp, comp) in enumerate(zip(target_components, components)):
                        if target_comp == comp:
                            same_position_components.append(i + 1)

                    if same_position_components:
                        key = ','.join(map(str, same_position_components))
                        key_hanzi = ''.join([target_components[int(pos) - 1] for pos in key.split(',')])
                        sisters["結構相同部件同位"].setdefault(key_hanzi, []).append(c)
                        found_sister = True
                    elif set(target_components) & set(components):
                        common_components = ''.join(sorted(set(target_components) & set(components)))
                        sisters["結構部件相同"].setdefault(common_components, []).append(c)
                        found_sister = True
                elif set(target_components) & set(components):
                    common_components = ''.join(sorted(set(target_components) & set(components)))
                    sisters["部件相同"].setdefault(common_components, []).append(c)
                    found_sister = True

        return sisters

    def _merge_sister_results(self, result_1: Dict[str, Dict[str, List[str]]], result_2: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, List[str]]]:
        """
        合併兩個 find_sister_characters 的結果
        """
        # 如果其中一個是獨體字,返回另一個
        if "獨體字" in result_1:
            return result_2 if result_2 and "獨體字" not in result_2 else result_1
        if "獨體字" in result_2:
            return result_1

        merged = {
            "拆法1結果": result_1,
            "拆法2結果": result_2
        }

        return merged

    def find_derived_characters(self, char: str, charset: Optional[Set[str]] = None) -> Dict[str, List[str]]:
        """
        搜尋包含指定字符作為部件的所有字符，將結果按部件分組

        參數:
        char (str): 要搜尋衍生字的字符
        charset (Optional[Set[str]]): 可選的字符集篩選

        回傳:
        Dict[str, List[str]]: 以部件為 key、衍生字列表為 value 的字典
        """
        MAX_DEPTH = 4
        derived_groups: Dict[str, List[str]] = {}
        decomposed_parts = set()
        structure_patterns = set()
        component_groups = set()
        visited_components = set()
        special_chars = set(IDC_CHARS)

        def extract_structure(components):
            if len(components) < 2:
                return

            full_structure = ''.join(comp for _, comp in components)
            structure_patterns.add(full_structure)

            for i in range(len(components)):
                for j in range(i + 2, len(components) + 1):
                    sub_structure = ''.join(comp for _, comp in components[i:j])
                    if any(c not in special_chars for c in sub_structure):
                        component_groups.add(sub_structure)

        def process_component(component, depth=0):
            if depth >= MAX_DEPTH or component in visited_components:
                return
            visited_components.add(component)

            if component and component not in special_chars:
                decomposed_parts.add(component)

            sub_components = self.decompose(component, max_depth=1)
            if sub_components:
                extract_structure(sub_components)

                for op, comp in sub_components:
                    if comp not in special_chars:
                        decomposed_parts.add(comp)
                        if depth < MAX_DEPTH and comp not in visited_components:
                            process_component(comp, depth + 1)

        # 初始處理目標字符
        initial_components = self.decompose(char, max_depth=1)
        process_component(char)

        # 建立部件到字符的映射
        for c, data in self.db.items():
            if c == char:
                continue

            # 套用字符集篩選（提前過濾）
            if charset is not None and c not in charset:
                continue

            try:
                target_components = self.decompose(c, max_depth=1)
                target_structure = ''.join(comp for _, comp in target_components)

                matching_components = set()  # 記錄匹配的部件

                # 檢查每個部件
                for _, comp in target_components:
                    if comp in decomposed_parts and comp not in special_chars:
                        matching_components.add(comp)
                        continue

                    # 遞迴檢查子部件
                    sub_comps = self.decompose(comp, max_depth=1)
                    for _, sub_comp in sub_comps:
                        if sub_comp in decomposed_parts and sub_comp not in special_chars:
                            matching_components.add(sub_comp)

                # 將字符加入對應的部件群組
                for matched_comp in matching_components:
                    if matched_comp not in derived_groups:
                        derived_groups[matched_comp] = []
                    derived_groups[matched_comp].append(c)

            except Exception:
                continue

        return derived_groups

    # === 字符拆解 ===

    def decompose(self, char: str, max_depth: int = 10, variant_index: int = 0) -> List[Tuple[str, str]]:
        """
        遞迴分解字符，顯示其結構（簡化版，不包含樹狀符號）

        參數:
        char (str): 要分解的字符
        max_depth (int): 最大遞迴深度
        variant_index (int): 使用第幾種拆法（0=ids_1, 1=ids_2, -1=全部顯示）

        回傳:
        List[Tuple[str, str]]: 分解後的結構列表，每個元素是一個元組 (tree_symbol, content)
        """
        return self._decompose_recursive(char, level=0, deep=True, max_depth=max_depth, variant_index=variant_index)

    def _decompose_recursive(self, char: str, level: int = 0, deep: bool = False, max_depth: int = 10, variant_index: int = 0) -> List[Tuple[str, str]]:
        """
        遞迴分解字符的內部實作

        參數:
        char (str): 要分解的字符
        level (int): 目前遞迴層級，用於縮排
        deep (bool): 是否進行深度拆解
        max_depth (int): 最大遞迴深度
        variant_index (int): 使用第幾種拆法（0=ids_1, 1=ids_2, -1=全部顯示）

        回傳:
        List[Tuple[str, str]]: 分解後的結構列表
        """
        if level >= max_depth:
            return [("｜   " * level + "└─ ", f"{char} (達到最大深度)")]

        data = self.db.get(char)
        if not data:
            return [("" if level == 0 else "｜   " * (level - 1) + "└─ ", char)]

        # 根據 variant_index 收集 IDS 變體
        ids_list = []
        if variant_index == -1:
            # 顯示所有拆法
            if data.get('ids_1'):
                ids_list.append(data['ids_1'])
            if data.get('ids_2'):
                ids_list.append(data['ids_2'])
        elif variant_index == 0:
            # 顯示第一種拆法
            if data.get('ids_1'):
                ids_list.append(data['ids_1'])
            elif data.get('ids_2'):  # 如果沒有 ids_1，使用 ids_2
                ids_list.append(data['ids_2'])
        elif variant_index == 1:
            # 顯示第二種拆法
            if data.get('ids_2'):
                ids_list.append(data['ids_2'])
            elif data.get('ids_1'):  # 如果沒有 ids_2，使用 ids_1
                ids_list.append(data['ids_1'])

        if not ids_list:
            return [("" if level == 0 else "｜   " * (level - 1) + "└─ ", char)]

        # 檢查是否為獨體字（沒有 IDC 字符）
        if all(idc not in ids for ids in ids_list for idc in IDC_CHARS):
            return [("" if level == 0 else "｜   " * (level - 1) + "└─ ", char)]

        result = [("", char)]

        for idx, ids in enumerate(ids_list):
            # 如果 IDS 只是字符本身（無拆解），直接顯示不再展開
            if ids == char:
                result.append(("｜   " * level, char))
                # 如果後面還有其他拆法，添加分隔符
                if idx < len(ids_list) - 1:
                    result.append(("｜   " * level, "或"))
                continue

            result.append(("｜   " * level, ids[0]))

            components = self.parse_ids(ids)[0][1:]
            for i, comp in enumerate(components):
                is_last = (i == len(components) - 1)
                prefix = "｜   " * level + ("└─ " if is_last else "├─ ")

                if deep and not comp.startswith('&') and comp not in IDC_CHARS:
                    sub_data = self.db.get(comp)
                    if sub_data and (sub_data.get('ids_1') or sub_data.get('ids_2')):
                        result.append((prefix, comp))
                        sub_result = self._decompose_recursive(comp, level + 1, deep, max_depth, variant_index)
                        result.extend(sub_result[1:])
                    else:
                        result.append((prefix, comp))
                else:
                    result.append((prefix, comp))

            # 在完成當前 IDS 的所有內容後，如果後面還有其他拆法，添加分隔符
            if idx < len(ids_list) - 1:
                result.append(("｜   " * level, "或"))

        return result

    # === IDS 變體管理 ===

    def get_ids_variants(self, char: str) -> List[str]:
        """
        取得字符的所有 IDS 拆法變體

        參數:
        char (str): 要查詢的字符

        回傳:
        List[str]: IDS 拆法列表，例如 ['⿰木木', '⿱某某']
                   如果字符不存在或沒有拆法，返回空列表
        """
        data = self.db.get(char)
        if not data:
            return []

        variants = []
        if data.get('ids_1'):
            variants.append(data['ids_1'])
        if data.get('ids_2'):
            variants.append(data['ids_2'])

        return variants

    # === 工具函數 ===

    @staticmethod
    def clean_display_text(text: str) -> str:
        """
        直接返回原始文本，不進行任何過濾

        依賴字型的 fallback 機制來正確顯示所有字符，
        包括 CJK 擴展區罕用字（U+20000-U+3134F）

        參數:
        text (str): 原始文本

        回傳:
        str: 原始文本（不做任何修改）
        """
        return text

    @staticmethod
    def is_error_message(text: str) -> bool:
        """
        檢查文字是否為錯誤訊息

        參數:
        text (str): 要檢查的文字

        回傳:
        bool: 是否為錯誤訊息
        """
        if not text or not text.strip():
            return True

        error_indicators = [
            ERROR_NO_MATCH_FOUND,
            ERROR_UNKNOWN_CHAR,
            ERROR_SEARCH_FAILED,
            "未找到",
            "無法",
            "錯誤",
            "(達到最大深度)",
            "達到最大深度"
        ]
        return any(indicator in text for indicator in error_indicators)

    @staticmethod
    def is_valid_character(char: str) -> bool:
        """
        檢查字符是否適合進行分析

        參數:
        char (str): 要檢查的字符

        回傳:
        bool: 是否為有效字符
        """
        if not char or not char.strip():
            return False

        # 檢查是否為錯誤訊息
        if HanziCore.is_error_message(char):
            return False

        # 檢查是否為單個字符（排除多字符錯誤訊息）
        stripped_char = char.strip()
        if len(stripped_char) > 1:
            # 允許某些特殊情況，如 Unicode 格式
            if not stripped_char.startswith(('U+', 'uni', 'u')):
                return False

        return True

    @staticmethod
    def extract_character(text: str) -> Optional[str]:
        """
        從顯示文本中智能提取實際字符

        參數:
        text (str): 顯示的文本字符串

        回傳:
        Optional[str]: 提取的字符，如果無法提取則返回 None
        """
        if not text or not text.strip():
            return None

        # 處理特殊標記（如 "王 (達到最大深度)"）
        if " (達到最大深度)" in text:
            char = text.replace(" (達到最大深度)", "").strip()
            if char and not HanziCore.is_error_message(char):
                return char

        # 檢查是否為錯誤訊息（在特殊標記處理之後）
        if HanziCore.is_error_message(text):
            return None

        # 處理樹狀結構格式（如 "｜   └─ 王"）
        # 移除樹狀結構符號
        tree_symbols = ["｜", "├─", "└─", " "]
        cleaned = text
        for symbol in tree_symbols:
            cleaned = cleaned.replace(symbol, " ")

        # 提取最後一個非空部分
        parts = [p.strip() for p in cleaned.split() if p.strip()]
        if parts:
            candidate = parts[-1]
            if not HanziCore.is_error_message(candidate):
                return candidate

        # 如果以上都失敗，嘗試直接返回清理後的字符串
        stripped = text.strip()
        if stripped and not HanziCore.is_error_message(stripped):
            return stripped

        return None


# === 獨立執行測試 ===

if __name__ == '__main__':
    """測試核心引擎功能"""

    print("=== Hanzi Component Explorer - 核心引擎測試 ===\n")

    # 初始化核心引擎
    try:
        core = HanziCore('data/ids.pdata')
        print(f"✅ 資料庫載入成功：{len(core.db)} 個字符\n")
    except Exception as e:
        print(f"❌ 資料庫載入失敗：{e}")
        exit(1)

    # 測試 1：字符查詢
    print("【測試 1：字符查詢】")
    test_char = '木'
    data = core.get_data(test_char)
    if data:
        char_data = data[test_char]
        print(f"字符：{char_data['char']}")
        print(f"Unicode：{char_data['unicode']}")
        print(f"IDS 1：{char_data.get('ids_1', '')}")
        if char_data.get('ids_2'):
            print(f"IDS 2：{char_data['ids_2']}")
        print()

    # 測試 2：Unicode 查詢
    print("【測試 2：Unicode 查詢】")
    unicode_query = 'U+6728'
    data = core.get_data(unicode_query)
    if data:
        char = list(data.keys())[0]
        print(f"查詢：{unicode_query} → 字符：{char}\n")

    # 測試 3：部件搜尋
    print("【測試 3：部件搜尋】")
    results = core.search('木')
    print(f"包含「木」的字符（前 10 個）：{' '.join(results[:10])}\n")

    # 測試 4：字符拆解
    print("【測試 4：字符拆解】")
    test_char = '森'
    decomposed = core.decompose(test_char, max_depth=3)
    print(f"字符「{test_char}」的拆解結構：")
    for tree, content in decomposed:
        print(f"{tree}{content}")
    print()

    # 測試 5：同字根搜尋
    print("【測試 5：同字根搜尋】")
    test_char = '林'
    sisters = core.find_sister_characters(test_char)
    for category, groups in sisters.items():
        if groups:
            print(f"{category}：")
            for key, chars in groups.items():
                print(f"  {key}：{' '.join(chars[:5])}")
    print()

    # 測試 6：衍生字搜尋
    print("【測試 6：衍生字搜尋】")
    test_char = '木'
    derived = core.find_derived_characters(test_char)
    if derived:
        print(f"包含「{test_char}」的衍生字（前 3 組）：")
        for i, (component, chars) in enumerate(list(derived.items())[:3]):
            print(f"  部件 {component}：{' '.join(chars[:8])}")
    print()

    print("✅ 所有測試完成！")
