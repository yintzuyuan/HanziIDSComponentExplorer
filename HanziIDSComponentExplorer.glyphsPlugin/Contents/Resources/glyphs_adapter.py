#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hanzi Component Explorer - Glyphs 適配層
封裝所有 Glyphs API 呼叫，隔離 Glyphs 依賴

© 2025 TzuYuan Yin
"""

from __future__ import division, print_function, unicode_literals

from typing import List, Optional, Any
from GlyphsApp import Glyphs, UPDATEINTERFACE


# 顏色標籤常數
COLOR_RED = 0
COLOR_ORANGE = 1
COLOR_BROWN = 2
COLOR_YELLOW = 3
COLOR_LIGHT_GREEN = 4
COLOR_DARK_GREEN = 5
COLOR_LIGHT_BLUE = 6
COLOR_DARK_BLUE = 7
COLOR_PURPLE = 8
COLOR_MAGENTA = 9
COLOR_LIGHT_GRAY = 10
COLOR_CHARCOAL = 11

# 預設篩選顏色（紅色和橘色）
DEFAULT_FILTER_COLORS = [COLOR_RED, COLOR_ORANGE]


class GlyphsAdapter:
    """Glyphs API 適配器"""

    # === 字型資料存取 ===

    @staticmethod
    def get_current_font():
        """
        取得當前開啟的字型

        回傳:
        Font: Glyphs 字型物件，如果沒有開啟字型則返回 None
        """
        return Glyphs.font

    @staticmethod
    def get_font_characters(font=None) -> List[str]:
        """
        取得字型檔中所有字符的列表（支援多 Unicode 值）

        參數:
        font: Glyphs 字型物件（None 時使用當前字型）

        回傳:
        List[str]: 字型中存在的字符列表（去重）

        說明:
        - 優先使用 glyph.unicodes 屬性（支援多 Unicode 值字符）
        - 向後相容 glyph.unicode 單值模式
        - 自動過濾無效 Unicode 值
        """
        if font is None:
            font = Glyphs.font

        if not font:
            return []

        characters = []
        seen_chars = set()  # 用於去重

        try:
            if hasattr(font, 'glyphs'):
                for glyph in font.glyphs:
                    # 優先使用 glyph.unicodes（支援多 Unicode 值）
                    if hasattr(glyph, 'unicodes') and glyph.unicodes:
                        for unicode_val in glyph.unicodes:
                            try:
                                char = chr(int(unicode_val, 16))
                                if char not in seen_chars:
                                    characters.append(char)
                                    seen_chars.add(char)
                            except (ValueError, OverflowError):
                                # 無效的 Unicode 值，跳過
                                continue
                    elif glyph.unicode:
                        # 向後相容：舊版本或單 Unicode 值
                        try:
                            char = chr(int(glyph.unicode, 16))
                            if char not in seen_chars:
                                characters.append(char)
                                seen_chars.add(char)
                        except (ValueError, OverflowError):
                            # 無效的 Unicode 值，跳過
                            continue
        except Exception as e:
            import traceback
            print(traceback.format_exc())

        return characters

    @staticmethod
    def get_glyph_color(font, char: str) -> Optional[int]:
        """
        取得 glyph 的顏色標籤

        參數:
        font: Glyphs 字型物件
        char (str): 要查詢的字符

        回傳:
        Optional[int]: 顏色標籤編號，如果沒有顏色或找不到 glyph 則返回 None
        """
        if not font:
            return None

        try:
            glyph = None

            # 方法1: 直接字符查詢（推薦方式）
            if char in font.glyphs:
                glyph = font.glyphs[char]
            # 方法2: Unicode 值查詢（備用方式）
            else:
                unicode_val = f"{ord(char):04X}"
                standard_name = f"uni{unicode_val}"
                if standard_name in font.glyphs:
                    glyph = font.glyphs[standard_name]
                elif unicode_val in font.glyphs:
                    glyph = font.glyphs[unicode_val]
                # 方法3: 使用 glyphForUnicode
                else:
                    try:
                        unicode_int = ord(char)
                        glyph = font.glyphForUnicode(unicode_int)
                    except AttributeError:
                        pass

            if glyph and hasattr(glyph, 'color'):
                return glyph.color

        except Exception:
            pass

        return None

    @staticmethod
    def filter_by_color(chars: List[str], font, colors: List[int]) -> List[str]:
        """
        根據顏色標籤篩選字符列表
        使用與官方 Smart Filter 相同的邏輯: glyph.color == target_color

        參數:
        chars (List[str]): 字符列表
        font: Glyphs 字型物件
        colors (List[int]): 要篩選的顏色列表

        回傳:
        List[str]: 篩選後的字符列表
        """
        if not font or not colors:
            return chars

        filtered_results = []

        for char in chars:
            try:
                glyph = None

                # 官方 Smart Filter 邏輯：直接檢查 glyph.color 屬性
                # 方法1: 直接字符查詢（推薦方式）
                if char in font.glyphs:
                    glyph = font.glyphs[char]
                # 方法2: Unicode 值查詢（備用方式）
                else:
                    unicode_val = f"{ord(char):04X}"
                    # 嘗試標準 glyph name 格式
                    standard_name = f"uni{unicode_val}"
                    if standard_name in font.glyphs:
                        glyph = font.glyphs[standard_name]
                    # 嘗試直接 Unicode 查詢
                    elif unicode_val in font.glyphs:
                        glyph = font.glyphs[unicode_val]
                    # 方法3: 使用 glyphForUnicode (如果可用)
                    else:
                        try:
                            unicode_int = ord(char)
                            test_glyph = font.glyphForUnicode(unicode_int)
                            if test_glyph:
                                glyph = test_glyph
                        except AttributeError:
                            pass

                    if not glyph:
                        continue

                # Smart Filter 核心邏輯：檢查 glyph.color 是否在目標顏色列表中
                if glyph and hasattr(glyph, 'color'):
                    glyph_color = glyph.color
                    if glyph_color is not None and glyph_color in colors:
                        filtered_results.append(char)

            except Exception:
                import traceback
                print(traceback.format_exc())
                continue

        return filtered_results

    # === 編輯操作 ===

    @staticmethod
    def get_selected_character(font=None) -> Optional[str]:
        """
        取得當前選取的字符

        參數:
        font: Glyphs 字型物件（None 時使用當前字型）

        回傳:
        Optional[str]: 當前選取的字符，如果沒有選取則返回 None
        """
        if font is None:
            font = Glyphs.font

        if font and font.selectedLayers:
            layer = font.selectedLayers[0]
            if layer and layer.parent:
                unicode_val = layer.parent.unicode
                if unicode_val:
                    return unicode_val

        return None

    @staticmethod
    def insert_to_tab(font, text: str):
        """
        插入文字到編輯分頁的游標位置

        參數:
        font: Glyphs 字型物件
        text (str): 要插入的文字
        """
        if not font:
            return

        tab = font.currentTab if font else None
        if tab is None:
            return

        cursor = tab.layersCursor
        current_text = tab.text or ""
        # 插入文字到游標後
        new_text = current_text[:cursor] + text + current_text[cursor:]
        tab.text = new_text
        tab.layersCursor = cursor + len(text)

    # === IME 輸入狀態偵測 ===

    @staticmethod
    def is_ime_input_active() -> bool:
        """
        檢查是否有 IME 輸入中（未確認的注音/拼音）

        透過 NSTextInputClient 協議的 hasMarkedText 方法偵測。
        當用戶打字但尚未按下 Enter 確認時，會有 "marked text"。

        回傳:
            bool: True 表示 IME 輸入中，應跳過更新

        技術細節:
        - graphicView 是 GSGlyphEditViewControllerProtocol 的屬性
        - Python API 未暴露此屬性，需透過 PyObjC 直接存取
        - graphicView 實作 NSTextInputClient 協議，提供 hasMarkedText 方法
        """
        try:
            font = Glyphs.font
            if not font or not font.currentTab:
                return False

            # 透過 PyObjC 直接存取 graphicView（Python API 未暴露此屬性）
            # graphicView 實作 NSTextInputClient 協議
            tab = font.currentTab
            if hasattr(tab, 'graphicView'):
                # 嘗試作為屬性存取
                graphic_view = tab.graphicView
                # 如果是 callable（方法），則呼叫它
                if callable(graphic_view):
                    graphic_view = graphic_view()
                if graphic_view and hasattr(graphic_view, 'hasMarkedText'):
                    return graphic_view.hasMarkedText()
        except Exception:
            pass

        return False

    # === 事件監聽 ===

    @staticmethod
    def register_callback(callback, event_type=UPDATEINTERFACE):
        """
        註冊事件回調

        參數:
        callback: 回調函數
        event_type: 事件類型（預設為 UPDATEINTERFACE）
        """
        Glyphs.addCallback(callback, event_type)

    @staticmethod
    def unregister_callback(callback, event_type=UPDATEINTERFACE):
        """
        移除事件回調

        參數:
        callback: 回調函數
        event_type: 事件類型（預設為 UPDATEINTERFACE）
        """
        try:
            Glyphs.removeCallback(callback, event_type)
        except:
            pass

    # === 通知 ===

    @staticmethod
    def show_notification(title: str, message: str):
        """
        顯示系統通知

        參數:
        title (str): 通知標題
        message (str): 通知內容
        """
        Glyphs.showNotification(title, message)


class GlyphsSettings:
    """Glyphs 設定管理器（封裝 Glyphs.defaults）"""

    PREFIX = "com.YinTzuYuan.HanziIDSComponentExplorer"

    @classmethod
    def get(cls, key: str, default=None) -> Any:
        """
        讀取設定值

        參數:
        key (str): 設定鍵名
        default: 預設值

        回傳:
        Any: 設定值，如果不存在則返回預設值
        """
        full_key = f"{cls.PREFIX}.{key}"
        value = Glyphs.defaults.get(full_key)
        return value if value is not None else default

    @classmethod
    def set(cls, key: str, value: Any):
        """
        儲存設定值

        參數:
        key (str): 設定鍵名
        value (Any): 要儲存的值
        """
        full_key = f"{cls.PREFIX}.{key}"
        Glyphs.defaults[full_key] = value

    @classmethod
    def remove(cls, key: str):
        """
        刪除設定值

        參數:
        key (str): 設定鍵名
        """
        full_key = f"{cls.PREFIX}.{key}"
        try:
            del Glyphs.defaults[full_key]
        except KeyError:
            pass


# === 測試程式碼（僅在 Glyphs Script Editor 中執行）===

if __name__ == '__main__':
    """測試 Glyphs 適配器功能"""

    print("=== Hanzi Component Explorer - Glyphs 適配器測試 ===\n")

    # 測試 1：取得當前字型
    print("【測試 1：取得當前字型】")
    font = GlyphsAdapter.get_current_font()
    if font:
        print(f"✅ 字型名稱：{font.familyName}")
        print(f"✅ Glyph 數量：{len(font.glyphs)}\n")
    else:
        print("❌ 沒有開啟字型\n")

    # 測試 2：取得字型字符
    print("【測試 2：取得字型字符】")
    chars = GlyphsAdapter.get_font_characters(font)
    if chars:
        print(f"✅ 字型包含 {len(chars)} 個字符")
        print(f"前 10 個字符：{' '.join(chars[:10])}\n")
    else:
        print("❌ 無法取得字型字符\n")

    # 測試 3：顏色篩選
    print("【測試 3：顏色篩選】")
    if font and chars:
        # 取前 100 個字符測試
        test_chars = chars[:100]
        red_chars = GlyphsAdapter.filter_by_color(test_chars, font, [COLOR_RED])
        orange_chars = GlyphsAdapter.filter_by_color(test_chars, font, [COLOR_ORANGE])
        print(f"紅色標籤字符：{len(red_chars)} 個")
        print(f"橘色標籤字符：{len(orange_chars)} 個\n")

    # 測試 4：設定讀寫
    print("【測試 4：設定讀寫】")
    GlyphsSettings.set("testKey", "testValue")
    value = GlyphsSettings.get("testKey")
    print(f"✅ 設定讀寫測試：{value}\n")

    # 測試 5：取得選取字符
    print("【測試 5：取得選取字符】")
    selected = GlyphsAdapter.get_selected_character(font)
    if selected:
        print(f"✅ 當前選取字符：{selected}\n")
    else:
        print("ℹ️ 沒有選取字符\n")

    print("✅ 所有測試完成！")
