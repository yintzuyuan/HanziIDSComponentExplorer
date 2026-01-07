# MenuTitle: 漢字IDS部件查詢
# -*- coding: utf-8 -*-
"""
Hanzi Component Explorer - Glyphs UI 層
使用 vanilla 框架的 Glyphs 外掛介面

© 2025 TzuYuan Yin
"""

from __future__ import division, print_function, unicode_literals

import os
import re
import time
from typing import Optional, Set, List

import vanilla
from AppKit import (NSFont, NSAttributedString, NSMutableAttributedString,
                    NSFontAttributeName, NSForegroundColorAttributeName,
                    NSKernAttributeName, NSParagraphStyleAttributeName,
                    NSBaselineOffsetAttributeName, NSMutableParagraphStyle,
                    NSColor, NSFontManager, NSOpenPanel,
                    NSObject, NSImage, NSFontDescriptor,
                    NSFontFamilyAttribute, NSNotificationCenter,
                    NSTableViewNoColumnAutoresizing, NSLineBreakByClipping)
import CoreText

from hanzi_core import HanziCore
from glyphs_adapter import GlyphsAdapter, GlyphsSettings
from localization import L


# 字體大小設定
RELATED_CHARS_FONT_SIZE = 20  # 右側相關字區域
CONTENT_FONT_SIZE = 14        # 左側詳細資訊區
RESULT_LIST_FONT_SIZE = 13    # 中間結果列表

# 右側相關字區域排版設定
RELATED_CHARS_KERN = 0.0      # 字距（字符間距，單位：點）- 預設值
RELATED_CHARS_LINE_HEIGHT = 1.2  # 行高倍數（相對於字體大小）

# Glyphs 顏色 ID 到 RGB 值的映射（12 種顏色）
GLYPH_COLOR_MAP = {
    0: (0.85, 0.26, 0.26, 1.0),   # 紅
    1: (0.97, 0.56, 0.26, 1.0),   # 橘
    2: (0.65, 0.48, 0.32, 1.0),   # 棕
    3: (0.97, 0.90, 0.26, 1.0),   # 黃
    4: (0.67, 0.90, 0.26, 1.0),   # 淺綠
    5: (0.26, 0.60, 0.26, 1.0),   # 深綠
    6: (0.26, 0.90, 0.97, 1.0),   # 淺藍
    7: (0.26, 0.56, 0.90, 1.0),   # 深藍
    8: (0.51, 0.26, 0.90, 1.0),   # 紫
    9: (0.90, 0.26, 0.67, 1.0),   # 洋紅
    10: (0.75, 0.75, 0.75, 1.0),  # 淺灰
    11: (0.50, 0.50, 0.50, 1.0),  # 深灰
}



# 篩選選單處理器（使用獨立類別確保 ObjC 方法正確註冊）
filter_handler_class_name = f"FilterMenuHandler_{int(time.time() * 1000)}"


class _FilterMenuHandlerBase(NSObject):
    """篩選選單動作處理器"""

    def initWithTool_(self, tool):
        self.tool = tool
        return self

    def openColorSelector_(self, sender):
        self.tool.show_color_selector(None)

    def selectFontCharset_(self, sender):
        self.tool.selectFontCharset()

    def selectCustomCharset_(self, sender):
        self.tool.selectCustomCharset()


# 使用動態名稱避免重複定義
FilterMenuHandler = type(
    filter_handler_class_name,
    (_FilterMenuHandlerBase,),
    {}
)



# 對話框色塊點擊處理器（用於顏色選擇對話框）
dialog_handler_class_name = f"DialogColorBlockHandler_{int(time.time() * 1000)}"

DialogColorBlockHandler = type(
    dialog_handler_class_name,
    (NSObject,),
    {
        'initWithTool_': lambda self, tool: setattr(self, 'tool', tool) or self,
        'handleBlockClick_': lambda self, gesture: (
            self.tool.toggle_color_block_selection(
                self.tool.dialog_color_block_map.get(id(gesture.view()))
            ) if id(gesture.view()) in self.tool.dialog_color_block_map else None
        )
    }
)


# 選取變化監聽處理器（用於右側相關字區域）
selection_observer_class_name = f"SelectionObserverHandler_{int(time.time() * 1000)}"

SelectionObserverHandler = type(
    selection_observer_class_name,
    (NSObject,),
    {
        'initWithTool_': lambda self, tool: setattr(self, 'tool', tool) or self,
        'textViewSelectionDidChange_': lambda self, notification: (
            self.tool.on_selection_changed(notification)
        )
    }
)


class HanziComponentSearchTool:
    """Glyphs 外掛主視窗"""

    # 字型快取（類別層級）
    _font_cache = {}  # key: (char, size), value: NSFont
    _CACHE_MAX_SIZE = 500  # 最大快取數量

    def __init__(self, title=None):
        # === 初始化核心引擎 ===
        self.core = HanziCore(self._find_data_path())

        # === 初始化 Glyphs 適配器 ===
        self.adapter = GlyphsAdapter()
        self.settings = GlyphsSettings()

        # === 初始化基本屬性 ===
        self.currentCharset: Set[str] = set()
        self.all_results = []  # 存儲 (tree, content) 格式的原始結果
        self.display_results = []  # 存儲顯示用的字符串
        self.current_char = None
        self.deep_analysis = self.settings.get("deepAnalysis", False)
        self.show_derived = False

        # 自動抓取設定（固定為 True）
        self.auto_fetch_enabled = True
        self.last_glyph_name = None

        # 模式切換：自動模式 vs 手動模式
        # 自動模式：選擇字符時清空搜尋框，使用多 Unicode 智能偵測
        # 手動模式：用戶輸入時觸發，直接搜尋輸入內容
        self.is_manual_mode = False

        # 顏色篩選設定
        self.filter_colors = self.settings.get("filterColors", [])
        self.dialog_color_block_map = {}  # 對話框色塊到 color_id 的映射
        self.color_blocks = {}  # 對話框 color_id 到色塊的映射
        self.color_block_states = {}  # 追蹤對話框色塊選取狀態

        # IDS 切換狀態
        self.current_ids_index = 0  # 目前顯示的 IDS 索引（0 或 1）
        self.available_ids = []  # 當前字符可用的 IDS 列表

        # === 字集管理（簡化版）===
        self.custom_charset_path = None  # 自訂字集檔案路徑
        self.custom_charset_name = None  # 自訂字集檔案名稱
        self.use_custom_charset = False  # 是否使用自訂字集

        # === 建立主視窗 ===
        window_title = title or L('window_title')
        self.w = vanilla.FloatingWindow((520, 440), window_title,
                                        minSize=(420, 300),
                                        maxSize=(1000, 1000),
                                        autosaveName="com.YinTzuYuan.HanziIDSComponentExplorer.MainWindow")

        # === 頂部搜尋區域 ===
        self.w.inputText = vanilla.SearchBox(
            (12, 12, -40, 22),  # 縮短右側，為插入按鈕留空間（24px 按鈕 + 4px 間距）
            placeholder=L('search_placeholder'),
            callback=self.search_callback
        )

        # 插入按鈕（右上角，搜尋框旁）
        insert_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "arrow.up.forward.square", None
        )
        self.w.insertButton = vanilla.ImageButton(
            (-34, 11, 24, 24),
            imageObject=insert_icon,
            callback=self.insert_selected_text,
            bordered=False
        )
        # 設定 hover/press 效果：使用工具列按鈕樣式
        ns_button = self.w.insertButton.getNSButton()
        ns_button.setBezelStyle_(11)  # NSBezelStyleTexturedRounded
        ns_button.setButtonType_(0)   # NSButtonTypeMomentaryLight - 點擊時高亮
        ns_button.setShowsBorderOnlyWhileMouseInside_(True)
        ns_button.setBordered_(True)
        ns_button.setToolTip_(L('btn_insert_tooltip'))
        self.w.insertButton.enable(False)  # 初始禁用

        # === 讀取設定 ===
        self.show_derived = self.settings.get("showDerived", False)

        # IDS 切換控制區（列表上方獨立一行，初始隱藏）
        self.w.idsSwitcher = vanilla.Group((114, 38, 130, 20))

        self.w.idsSwitcher.prevButton = vanilla.Button(
            (0, 0, 35, 20),
            "◀",
            callback=self.prev_ids,
            sizeStyle="small"
        )

        self.w.idsSwitcher.indicator = vanilla.TextBox(
            (40, 0, 50, 20),
            "1/2",
            alignment="center",
            sizeStyle="small"
        )

        self.w.idsSwitcher.nextButton = vanilla.Button(
            (95, 0, 35, 20),
            "▶",
            callback=self.next_ids,
            sizeStyle="small"
        )

        # 初始隱藏
        self.w.idsSwitcher.show(False)

        # === 左側資訊區 ===
        # 預覽區
        self.w.preview = vanilla.TextBox(
            (12, 38, 90, 90),
            "",
            alignment="center"
        )

        # 詳細資訊區（向下擴展到視窗底部）
        self.w.content = vanilla.TextEditor(
            (12, 130, 90, -42),
            "",
            readOnly=True
        )

        # === 中間結果列表 ===
        self.w.resultList = vanilla.List(
            (114, 60, 130, -42),
            [],
            selectionCallback=self.selection_callback
        )

        # 為結果列表設定 TW-Sung 字型
        result_list_font = self.get_font_for_char("漢", RESULT_LIST_FONT_SIZE)
        tableView = self.w.resultList.getNSTableView()
        for column in tableView.tableColumns():
            column.dataCell().setFont_(result_list_font)

        # 啟用橫向捲軸：禁用欄位自動調整，讓欄位可以超出視窗寬度
        tableView.setColumnAutoresizingStyle_(NSTableViewNoColumnAutoresizing)
        for column in tableView.tableColumns():
            column.setMinWidth_(130)
            column.setMaxWidth_(2000)
            # 停用文字省略，改為裁切（搭配橫向捲軸使用）
            column.dataCell().setLineBreakMode_(NSLineBreakByClipping)

        # === 右側相關字區域 ===
        self.w.relatedChars = vanilla.TextEditor(
            (256, 38, -12, -42),
            "",
            readOnly=True
        )

        # 相關字區域的字型會在 update_related_display 中動態設定

        # === 底部控制列 ===
        # 全字庫連結按鈕（左側區域下方，SF Symbols 圖示）
        try:
            # 使用 .zh 後綴強制顯示中文字元，符合「全字庫」的定位
            cns_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                "character.book.closed.zh", "CNS11643"
            )
        except Exception:
            cns_icon = None

        self.w.cnsLinkButton = vanilla.ImageButton(
            (12, -37, 24, 24),
            imageObject=cns_icon,
            callback=self.open_cns_link,
            bordered=False
        )
        # 設定 hover/press 效果：使用工具列按鈕樣式
        ns_button = self.w.cnsLinkButton.getNSButton()
        ns_button.setBezelStyle_(11)  # NSBezelStyleTexturedRounded
        ns_button.setButtonType_(0)   # NSButtonTypeMomentaryLight - 點擊時高亮
        ns_button.setShowsBorderOnlyWhileMouseInside_(True)
        ns_button.setBordered_(True)
        # 初始狀態：無字符時禁用
        self.w.cnsLinkButton.enable(False)

        # 深度拆解開關（中間區域下方）
        self.w.deepAnalysisCheckbox = vanilla.CheckBox(
            (114, -36, 80, 22),
            L('checkbox_deep_analysis'),
            callback=self.toggle_deep_analysis,
            value=self.deep_analysis
        )

        # 衍生字勾選框（右側區域左下角）
        self.w.showDerivedCheckbox = vanilla.CheckBox(
            (256, -36, 60, 22),
            L('checkbox_derived'),
            callback=self.toggle_derived_display,
            value=self.show_derived
        )

        # 篩選按鈕（右下角）
        filter_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "line.3.horizontal.decrease.circle",
            None
        )
        self.w.filterButton = vanilla.ImageButton(
            (-34, -37, 24, 24),
            imageObject=filter_icon,
            callback=self.show_filter_menu,
            bordered=False
        )
        # 設定 hover/press 效果：使用工具列按鈕樣式
        ns_button = self.w.filterButton.getNSButton()
        ns_button.setBezelStyle_(11)  # NSBezelStyleTexturedRounded
        ns_button.setButtonType_(0)   # NSButtonTypeMomentaryLight - 點擊時高亮
        ns_button.setShowsBorderOnlyWhileMouseInside_(True)
        ns_button.setBordered_(True)

        # === 載入字集設定 ===
        # 載入上次的自訂字集設定（如果有）
        saved_path = self.settings.get("customCharsetPath")
        if saved_path and os.path.exists(saved_path):
            self.custom_charset_path = saved_path
            self.custom_charset_name = os.path.basename(saved_path)
            self.use_custom_charset = True
            self.loadCustomCharset(saved_path)
        # 若無自訂字集，由下方 loadFontCharset 統一處理

        # 註：移除 setFrameUsingName_ 以避免載入舊版本的視窗尺寸設定
        # 未來可以考慮使用 GlyphsSettings 自行管理視窗位置和尺寸
        # 註：暫時也移除 setResizeIncrements_ 以避免視窗自動擴張問題
        # self.w.getNSWindow().setResizeIncrements_((1.0, 1.0))

        # 綁定視窗關閉事件
        self.w.bind("close", self.windowWillClose)

        # 建立事件處理器
        self.selectionObserver = SelectionObserverHandler.alloc().initWithTool_(self)
        self.filterMenuHandler = FilterMenuHandler.alloc().initWithTool_(self)
        self.dialogColorBlockHandler = DialogColorBlockHandler.alloc().initWithTool_(self)

        # 初始化顏色篩選 tooltip
        self.update_color_display()

        self.w.open()
        # 在視窗開啟後更新相關顯示
        self.update_related_display()
        # 設定右側相關字區域的選取監聽
        self.setup_selection_observer()

        # 註冊 Glyphs 回調以監聽字符變化
        self.adapter.register_callback(self.on_glyph_changed)

        # 載入字型檔字集作為預設篩選（不觸發搜尋，由 on_glyph_changed 統一處理）
        self.loadFontCharset(trigger_search=False)

        # 開啟時立即抓取當前字符並執行搜尋
        self.on_glyph_changed()

    def _find_data_path(self) -> str:
        """尋找資料庫路徑"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, 'data', 'ids.pdata')

    # === 統一篩選選單 ===

    def show_filter_menu(self, sender):
        """顯示統一篩選選單"""
        from AppKit import NSMenu, NSMenuItem, NSOnState, NSOffState

        menu = NSMenu.alloc().init()

        # 顏色篩選項目
        color_count = len(self.filter_colors)
        if color_count > 0:
            color_title = L('menu_color_filter_count').format(count=color_count)
        else:
            color_title = L('menu_color_filter')
        color_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            color_title, "openColorSelector:", ""
        )
        color_item.setTarget_(self.filterMenuHandler)
        menu.addItem_(color_item)

        # 分隔線
        menu.addItem_(NSMenuItem.separatorItem())

        # 字型檔項目
        font_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            L('charset_font'), "selectFontCharset:", ""
        )
        font_item.setTarget_(self.filterMenuHandler)
        font_item.setState_(NSOnState if not self.use_custom_charset else NSOffState)
        menu.addItem_(font_item)

        # 自訂字集項目
        if self.use_custom_charset and self.custom_charset_path:
            custom_title = os.path.basename(self.custom_charset_path)
        else:
            custom_title = L('charset_custom')
        custom_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            custom_title, "selectCustomCharset:", ""
        )
        custom_item.setTarget_(self.filterMenuHandler)
        custom_item.setState_(NSOnState if self.use_custom_charset else NSOffState)
        menu.addItem_(custom_item)

        # 在按鈕下方顯示選單
        button = sender.getNSButton()
        menu.popUpMenuPositioningItem_atLocation_inView_(
            None,
            (0, button.bounds().size.height),
            button
        )

    # === 字集管理 ===

    def selectFontCharset(self):
        """切換到字型檔字集"""
        self.use_custom_charset = False
        self.settings.remove("customCharsetPath")  # 清除儲存的自訂字集路徑
        self.loadFontCharset()
        # 更新相關顯示
        self.update_related_display()

    def selectCustomCharset(self):
        """選擇自訂字集檔案"""
        panel = NSOpenPanel.openPanel()
        panel.setAllowedFileTypes_(["txt", "hex"])

        if panel.runModal() == 1:
            path = panel.URLs()[0].path()
            self.custom_charset_path = path
            self.custom_charset_name = os.path.basename(path)
            self.use_custom_charset = True

            # 載入字集
            self.loadCustomCharset(path)

            # 保存設定
            self.settings.set("customCharsetPath", path)

            # 更新相關顯示
            self.update_related_display()

    def loadCustomCharset(self, path):
        """載入自訂字集檔案"""
        self.currentCharset.clear()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    code = line.split('#')[0].strip()
                    if code:
                        try:
                            if code.startswith('uni'):
                                code = code[3:]
                            self.currentCharset.add(chr(int(code, 16)))
                        except ValueError:
                            continue

            # 更新搜尋結果
            self.search_callback(None)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            # 載入失敗，切回字型檔
            self.use_custom_charset = False
            self.custom_charset_path = None
            self.custom_charset_name = None
            self.loadFontCharset()

    def loadFontCharset(self, trigger_search=True):
        """
        載入字型檔字符作為字集

        參數:
            trigger_search: 是否觸發搜尋更新（預設 True）
        """
        self.currentCharset.clear()

        # 取得目前字型的字符（透過 adapter）
        font = self.adapter.get_current_font()
        font_chars = self.adapter.get_font_characters(font)

        if font_chars:
            self.currentCharset.update(font_chars)

        # 更新搜尋結果（初始化時跳過，避免重複搜尋）
        if trigger_search:
            self.search_callback(None)

    def _adjust_result_list_column_width(self):
        """根據內容動態調整結果列表欄位寬度"""
        tableView = self.w.resultList.getNSTableView()
        if not self.display_results:
            return

        font = tableView.tableColumns()[0].dataCell().font()
        max_width = 130

        for item in self.display_results:
            attr_str = NSAttributedString.alloc().initWithString_attributes_(
                item, {NSFontAttributeName: font}
            )
            text_width = attr_str.size().width + 20
            if text_width > max_width:
                max_width = text_width

        for column in tableView.tableColumns():
            column.setWidth_(max_width)

    # === 自動抓取功能 ===

    def find_valid_unicode_for_char(self, glyph):
        """
        智能選擇資料庫中存在的 Unicode 值（多 Unicode 支援）

        參數:
        glyph: Glyphs glyph 物件

        回傳:
        str: 資料庫中存在的字符，如果都不存在則返回 None

        說明:
        1. 優先檢查 glyph.unicodes / glyph.unicode
        2. 如果沒有 Unicode 值，嘗試從 glyph name 解析（如 uni4FE1.001 → 4FE1）
        3. 返回第一個在資料庫中存在的字符
        """
        # 收集所有可能的 Unicode 值
        unicode_candidates = []

        # 優先使用 glyph.unicodes（如果存在）
        if hasattr(glyph, 'unicodes') and glyph.unicodes:
            unicode_candidates = list(glyph.unicodes)
        elif glyph.unicode:
            # 降級到單值
            unicode_candidates = [glyph.unicode]
        else:
            # 沒有 Unicode 值，嘗試從 glyph name 提取
            # 格式：
            # - uni4FE1, uni4FE1.001 (4 位)
            # - uniF0000 (5 位，Private Use Area)
            # - u10000, u10000.001 (5 位，Supplementary Plane)
            if glyph.name:
                base_unicode = None

                if glyph.name.startswith('uni'):
                    # 格式：uni + 4-5 位十六進位
                    name_without_prefix = glyph.name[3:]  # 移除 'uni'
                    base_unicode = name_without_prefix.split('.')[0]  # 移除 .001 等後綴
                elif glyph.name.startswith('u') and not glyph.name.startswith('uni'):
                    # 格式：u + 5-6 位十六進位（用於 U+10000 以上）
                    name_without_prefix = glyph.name[1:]  # 移除 'u'
                    base_unicode = name_without_prefix.split('.')[0]  # 移除 .001 等後綴

                # 驗證格式（4-6 位十六進位）
                if base_unicode and len(base_unicode) in [4, 5, 6] and all(c in '0123456789ABCDEFabcdef' for c in base_unicode):
                    unicode_candidates = [base_unicode.upper()]

        # 遍歷所有候選值，找到第一個在資料庫中存在的
        for unicode_val in unicode_candidates:
            try:
                char = chr(int(unicode_val, 16))
                # 檢查資料庫中是否存在
                if self.core.get_data(char):
                    return char
            except (ValueError, OverflowError):
                continue

        return None

    def get_current_glyph(self):
        """
        取得目前正在編輯的字符（透過 adapter）

        回傳:
        str: 目前編輯的字符，如果沒有則返回空字符串
        """
        font = self.adapter.get_current_font()
        return self.adapter.get_selected_character(font) or ""

    def on_glyph_changed(self, notification=None):
        """
        當前字符變化時的回調函式（透過 UPDATEINTERFACE 通知觸發）

        新行為（自動模式）：
        1. 清空搜尋框（不填入字符）
        2. 使用多 Unicode 智能偵測找到資料庫中存在的字符
        3. 設定 current_char 並觸發搜尋
        4. 進入自動模式（清除手動模式標記）

        參數:
        notification: 通知物件（可選）
        """
        try:
            if not self.auto_fetch_enabled:
                return

            # 檢查 IME 輸入狀態，跳過未確認的注音/拼音輸入
            if self.adapter.is_ime_input_active():
                return

            # 取得當前字型
            font = self.adapter.get_current_font()
            if not font or not font.selectedLayers:
                return

            # 取得當前 glyph
            layer = font.selectedLayers[0]
            if not layer or not layer.parent:
                return

            glyph = layer.parent
            current_glyph_name = glyph.name  # 使用 glyph name 作為識別

            # 只在字符改變時執行（避免過度觸發）
            if current_glyph_name == self.last_glyph_name:
                return

            self.last_glyph_name = current_glyph_name

            # 多 Unicode 智能選擇：找到資料庫中存在的字符
            valid_char = self.find_valid_unicode_for_char(glyph)

            if valid_char:
                # 進入自動模式
                self.is_manual_mode = False

                # 清空搜尋框
                self.w.inputText.set("")

                # 設定當前字符並觸發搜尋
                self.current_char = valid_char
                self.perform_search()

        except:
            import traceback
            print(traceback.format_exc())

    def toggle_auto_fetch(self, sender):
        """
        切換自動抓取功能

        參數:
        sender: 勾選框元件
        """
        self.auto_fetch_enabled = sender.get()

        # 如果開啟自動抓取，立即執行一次
        if self.auto_fetch_enabled:
            current_glyph = self.get_current_glyph()
            if current_glyph:
                self.w.inputText.set(current_glyph)
                self.perform_search()

    # === 搜尋功能 ===

    def search_callback(self, sender):
        """
        搜尋框輸入回調

        當用戶在搜尋框輸入時：
        1. 進入手動模式
        2. 執行搜尋
        """
        # 用戶開始輸入 → 進入手動模式
        input_text = self.w.inputText.get().strip()
        if input_text:
            self.is_manual_mode = True

        self.perform_search()

    def perform_search(self):
        """
        執行搜尋

        自動模式：使用 self.current_char（已由 on_glyph_changed 設定）
        手動模式：使用搜尋框內容
        """
        input_text = self.w.inputText.get().strip()

        # 自動模式：搜尋框為空，使用 current_char
        if not input_text:
            if self.current_char:
                # 自動模式：使用已設定的 current_char
                input_text = self.current_char
            else:
                return  # 無輸入，保持原顯示
        else:
            # 手動模式：使用搜尋框內容
            self.current_char = None  # 清除自動模式的字符

        # 處理 Unicode 格式
        if input_text.startswith(('uni', 'UNI')) and len(input_text) == 7:
            input_text = 'U+' + input_text[3:].upper()
        elif input_text.startswith(('u', 'U')) and len(input_text) == 6 and not input_text.startswith(('U+', 'u+')):
            input_text = 'U+' + input_text[1:].upper()

        # Unicode 查詢
        if input_text.startswith(('U+', 'u+')) or re.match(r'^[0-9A-Fa-f]{4,5}$', input_text):
            if not input_text.upper().startswith('U+'):
                input_text = 'U+' + input_text.upper()
            else:
                input_text = input_text.upper()

            char_data = self.core.get_data(input_text)
            if char_data:
                # 取得查詢到的字符
                found_char = list(char_data.keys())[0]
                # 根據深淺層狀態調整拆解深度
                depth = 10 if self.deep_analysis else 1
                self.all_results = self.core.decompose(found_char, max_depth=depth)
            else:
                return  # 找不到結果，保持原顯示
        else:
            # 字符查詢（優先嘗試拆解輸入的字本身）
            char_data = self.core.get_data(input_text)

            if char_data:
                # 找到字符，拆解它本身
                found_char = list(char_data.keys())[0]
                depth = 10 if self.deep_analysis else 1
                self.all_results = self.core.decompose(found_char, max_depth=depth)
            else:
                # 找不到字符，改為部件搜尋（顯示「顯示衍生字」時才執行）
                if self.show_derived:
                    charset = self.currentCharset if self.currentCharset else None
                    related_chars = self.core.search(input_text, charset)

                    if related_chars:
                        self.all_results = []
                        depth = 10 if self.deep_analysis else 1
                        for char in related_chars[:5]:  # 限制結果數量避免過慢
                            self.all_results.extend(self.core.decompose(char, max_depth=depth))
                    else:
                        return  # 找不到結果，保持原顯示
                else:
                    return  # 找不到結果，保持原顯示

        # 生成顯示結果並同時存儲
        self.display_results = [f"{tree}{content}" for tree, content in self.all_results]
        self.w.resultList.set(self.display_results)
        self._adjust_result_list_column_width()

        # 提取第一個有效字符
        if self.all_results:
            first_char = self._extract_valid_character_from_results(self.all_results)
            if first_char:
                self.update_char_info(first_char)

    def _extract_valid_character_from_results(self, results: List) -> Optional[str]:
        """從搜尋結果中提取有效字符"""
        idc_chars = '⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻〾'

        for tree, content in results:
            if not content.strip():
                continue
            if self.core.is_error_message(content):
                continue
            if content in idc_chars:
                continue
            if self.core.is_valid_character(content):
                return content

        return None

    def toggle_deep_analysis(self, sender):
        """切換深度拆解"""
        self.deep_analysis = sender.get()
        self.settings.set("deepAnalysis", self.deep_analysis)

        # 保存當前選中的 IDS 索引
        saved_ids_index = getattr(self, 'current_ids_index', 0)

        # 重新執行搜尋以更新結果
        self.search_callback(None)

        # 恢復 IDS 索引並刷新顯示
        if hasattr(self, 'available_ids') and len(self.available_ids) > saved_ids_index:
            self.current_ids_index = saved_ids_index
            self.refresh_ids_display()

    def prev_ids(self, sender):
        """切換到上一個 IDS"""
        if len(self.available_ids) > 1:
            self.current_ids_index = (self.current_ids_index - 1) % len(self.available_ids)
            self.refresh_ids_display()

    def next_ids(self, sender):
        """切換到下一個 IDS"""
        if len(self.available_ids) > 1:
            self.current_ids_index = (self.current_ids_index + 1) % len(self.available_ids)
            self.refresh_ids_display()

    def refresh_ids_display(self):
        """重新整理 IDS 顯示"""
        if not self.current_char or not self.available_ids:
            return

        data = self.core.get_data(self.current_char)
        if data:
            char_data = data[self.current_char]

            # 顯示所有可用的 IDS 拆法，並標示當前選中的
            if len(self.available_ids) == 1:
                ids_display = self.available_ids[0]
            else:
                ids_lines = []
                for i, ids in enumerate(self.available_ids):
                    if i == self.current_ids_index:
                        ids_lines.append(f"▶ {ids}")
                    else:
                        ids_lines.append(f"  {ids}")
                ids_display = "\n".join(ids_lines)

            detail_text = f"{char_data['char']}\n{char_data['unicode'].upper()}\n{ids_display}"
            detail_text = self.core.clean_display_text(detail_text)
            # 使用動態字型的 NSAttributedString
            attr_string = self.create_attributed_string(detail_text, CONTENT_FONT_SIZE)
            text_view = self.w.content.getNSTextView()
            text_view.textStorage().setAttributedString_(attr_string)

            # 更新指示器
            self.w.idsSwitcher.indicator.set(f"{self.current_ids_index + 1}/{len(self.available_ids)}")

            # 重新生成拆解樹（基於當前選中的 IDS）
            depth = 10 if self.deep_analysis else 1
            self.all_results = self.core.decompose(self.current_char, max_depth=depth, variant_index=self.current_ids_index)

            # 更新結果列表顯示
            self.display_results = [f"{tree}{content}" for tree, content in self.all_results]
            self.w.resultList.set(self.display_results)
            self._adjust_result_list_column_width()

            # 更新相關字顯示（基於當前選中的 IDS）
            self.update_related_display()

    # === 選擇處理 ===

    def selection_callback(self, sender):
        """
        處理結果列表中的選擇事件

        - IDC 符號：不執行任何動作
        - 漢字：只更新右側相關字區域，左側保持不變
        """
        selection = sender.getSelection()
        if selection:
            selected_item = sender[selection[0]]

            # 使用 core 的字符提取邏輯
            char = self.core.extract_character(selected_item)

            # IDC 符號不執行任何動作
            idc_chars = '⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻〾'
            if char in idc_chars:
                return

            if char and self.core.is_valid_character(char):
                # 只更新右側相關字區域，不更新左側
                self.update_related_display(char)

    def update_char_info(self, char):
        """更新字符資訊（支援 IDS 切換）"""
        self.current_char = char
        data = self.core.get_data(char)

        if data:
            char_data = data[char]
            # 使用 ids_1 和 ids_2 而非 ids
            ids_1 = char_data.get('ids_1', '')
            ids_2 = char_data.get('ids_2', '')

            # 收集所有可用的 IDS
            self.available_ids = [ids for ids in [ids_1, ids_2] if ids]

            # 重置索引
            self.current_ids_index = 0

            # 顯示所有可用的 IDS 拆法
            if self.available_ids:
                if len(self.available_ids) == 1:
                    ids_display = self.available_ids[0]
                else:
                    # 多個拆法時，列出所有並標示當前選中的
                    ids_lines = []
                    for i, ids in enumerate(self.available_ids):
                        if i == self.current_ids_index:
                            ids_lines.append(f"▶ {ids}")
                        else:
                            ids_lines.append(f"  {ids}")
                    ids_display = "\n".join(ids_lines)
            else:
                # 無 IDS 資料時顯示本字
                ids_display = char_data['char']

            detail_text = f"{char_data['char']}\n{char_data['unicode'].upper()}\n{ids_display}"
            # 清理可能造成顯示問題的字符
            detail_text = self.core.clean_display_text(detail_text)
            # 使用動態字型的 NSAttributedString
            attr_string = self.create_attributed_string(detail_text, CONTENT_FONT_SIZE)
            text_view = self.w.content.getNSTextView()
            text_view.textStorage().setAttributedString_(attr_string)

            # 控制切換器顯示
            if len(self.available_ids) > 1:
                self.w.idsSwitcher.show(True)
                self.w.idsSwitcher.indicator.set(f"{self.current_ids_index + 1}/{len(self.available_ids)}")
            else:
                self.w.idsSwitcher.show(False)

        # 更新相關顯示
        self.update_related_display()
        self.update_preview(char)

        # 更新全字庫按鈕狀態
        if hasattr(self.w, 'cnsLinkButton'):
            self.w.cnsLinkButton.enable(bool(self.current_char))

    # === 顏色選擇器 ===

    def show_color_selector(self, sender):
        """開啟顏色選擇對話框（符合 macOS HIG）"""
        from AppKit import NSBox, NSColor, NSBoxCustom, NSClickGestureRecognizer

        # 建立 Sheet 對話框（緊湊版）
        # 色塊：6 × 20px + 5 × 4px 間距 = 140px
        # 視窗寬度：140 + 左右邊距 16×2 = 172，取 175px
        self.colorSheet = vanilla.Sheet((175, 140), self.w)

        # 標題列：左側標題，右側輔助按鈕
        self.colorSheet.title = vanilla.TextBox(
            (16, 14, 60, 17),
            L('color_picker_title'),
            sizeStyle="small"
        )

        # 輔助按鈕（標題列右側，SF Symbol 圖示）
        # 統一邊距 16px，按鈕間距 4px
        select_all_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "checkmark.circle.fill", None
        )
        self.colorSheet.selectAllButton = vanilla.ImageButton(
            (-60, 12, 20, 20),
            imageObject=select_all_icon,
            callback=self.select_all_colors,
            bordered=False
        )
        self.colorSheet.selectAllButton.getNSButton().setToolTip_(L('btn_select_all'))

        deselect_icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "xmark.circle", None
        )
        self.colorSheet.deselectAllButton = vanilla.ImageButton(
            (-36, 12, 20, 20),
            imageObject=deselect_icon,
            callback=self.deselect_all_colors,
            bordered=False
        )
        self.colorSheet.deselectAllButton.getNSButton().setToolTip_(L('btn_clear'))

        # 色塊容器（左對齊，與標題對齊）
        # 寬度：6 × 20 + 5 × 4 = 140px，高度：2 × 20 + 1 × 4 = 44px
        self.colorSheet.colorBlockGroup = vanilla.Group((16, 38, 140, 48))
        group_view = self.colorSheet.colorBlockGroup.getNSView()

        # 清空映射
        self.dialog_color_block_map = {}
        self.color_blocks = {}
        self.color_block_states = {}

        # 建立 12 色視覺色塊矩陣（6x2 佈局，緊湊間距）
        chip_size = 20
        spacing = 4

        for color_id in range(12):
            row = color_id // 6
            col = color_id % 6
            x = col * (chip_size + spacing)
            # 反轉 y 座標：row 0 在上方，row 1 在下方
            y = (1 - row) * (chip_size + spacing)

            # 判斷是否已選取
            selected = color_id in self.filter_colors
            self.color_block_states[color_id] = selected

            # 取得顏色
            r, g, b, _ = GLYPH_COLOR_MAP[color_id]

            # 建立 NSBox 作為色塊
            color_box = NSBox.alloc().initWithFrame_(
                ((x, y), (chip_size, chip_size))
            )
            color_box.setBoxType_(NSBoxCustom)

            # 設定填充顏色
            fill_color = NSColor.colorWithRed_green_blue_alpha_(r, g, b, 1.0)
            color_box.setFillColor_(fill_color)

            # 設定圓角為完全圓形
            color_box.setCornerRadius_(chip_size / 2.0)

            # 儲存色塊映射
            self.dialog_color_block_map[id(color_box)] = color_id
            self.color_blocks[color_id] = color_box

            # 設定邊框（選取時顯示）
            self._set_color_block_border(color_box, selected)

            # 添加點擊手勢識別器
            click_recognizer = NSClickGestureRecognizer.alloc().initWithTarget_action_(
                self.dialogColorBlockHandler,
                "handleBlockClick:"
            )
            color_box.addGestureRecognizer_(click_recognizer)

            # 加入到 Group
            group_view.addSubview_(color_box)

        # 主要操作按鈕（底部居中，small size）
        # 兩按鈕寬 60*2 + 間距 6 = 126，起始 x = (175-126)/2 ≈ 25
        self.colorSheet.cancelButton = vanilla.Button(
            (25, -38, 60, 24),
            L('btn_cancel'),
            callback=self.cancel_color_selection,
            sizeStyle="small"
        )

        self.colorSheet.applyButton = vanilla.Button(
            (91, -38, 60, 24),
            L('btn_apply'),
            callback=self.apply_color_selection,
            sizeStyle="small"
        )

        self.colorSheet.open()

        # 設定快捷鍵
        cancel_ns_button = self.colorSheet.cancelButton.getNSButton()
        cancel_ns_button.setKeyEquivalent_(chr(27))  # ESC 鍵

        apply_ns_button = self.colorSheet.applyButton.getNSButton()
        apply_ns_button.setKeyEquivalent_("\r")  # Enter 鍵（預設按鈕）

    def _set_color_block_border(self, color_box, selected):
        """設定色塊邊框樣式（統一管理選取狀態的視覺呈現）"""
        if selected:
            color_box.setBorderType_(1)  # NSLineBorder
            color_box.setBorderWidth_(2.0)
            color_box.setBorderColor_(NSColor.secondaryLabelColor())
        else:
            color_box.setBorderType_(0)
            color_box.setBorderWidth_(0)

    def toggle_color_block_selection(self, color_id):
        """切換色塊選取狀態"""
        if color_id is None:
            return

        # 切換狀態
        current_state = self.color_block_states.get(color_id, False)
        new_state = not current_state
        self.color_block_states[color_id] = new_state

        # 更新色塊邊框
        color_box = self.color_blocks.get(color_id)
        if color_box:
            self._set_color_block_border(color_box, new_state)

    def select_all_colors(self, sender):
        """全選所有顏色"""
        for color_id in range(12):
            self.color_block_states[color_id] = True
            color_box = self.color_blocks.get(color_id)
            if color_box:
                self._set_color_block_border(color_box, True)

    def deselect_all_colors(self, sender):
        """取消全選所有顏色"""
        for color_id in range(12):
            self.color_block_states[color_id] = False
            color_box = self.color_blocks.get(color_id)
            if color_box:
                self._set_color_block_border(color_box, False)

    def apply_color_selection(self, sender):
        """套用顏色選擇（視覺色塊版本）"""
        # 收集已選顏色（從色塊狀態讀取）
        selected_colors = []
        for color_id, selected in self.color_block_states.items():
            if selected:
                selected_colors.append(color_id)

        # 更新 filter_colors
        self.filter_colors = selected_colors

        # 儲存設定
        self.settings.set("filterColors", self.filter_colors)

        # 更新色塊顯示
        self.update_color_display()

        # 更新相關字顯示
        self.update_related_display()

        # 關閉對話框
        self.colorSheet.close()

    def cancel_color_selection(self, sender):
        """取消顏色選擇"""
        self.colorSheet.close()

    def update_color_display(self):
        """更新篩選按鈕的 tooltip 顯示選取數量"""
        count = len(self.filter_colors)
        if count == 0:
            tooltip = L('tooltip_no_filter')
        else:
            tooltip = L('tooltip_filter_count').format(count=count)

        self.w.filterButton.getNSButton().setToolTip_(tooltip)

    # === 相關字顯示 ===

    def toggle_derived_display(self, sender):
        """處理衍生字顯示切換"""
        self.show_derived = sender.get()

        # 儲存設定
        self.settings.set("showDerived", self.show_derived)

        # 更新顯示
        self.update_related_display()

    def update_related_display(self, char=None):
        """
        更新相關字符顯示

        參數:
        char: 可選，指定要顯示的字符。若為 None 則使用 self.current_char。
        """
        # 若傳入 char 則使用，否則使用 self.current_char
        display_char = char if char is not None else getattr(self, 'current_char', None)
        if display_char is None:
            return

        display_lines = []
        charset = self.currentCharset if self.currentCharset else None

        # 取得關聯字結果（透過 core），使用當前選中的 IDS 拆法
        variant_index = getattr(self, 'current_ids_index', 0)
        sisters = self.core.find_sister_characters(display_char, charset, variant_index)
        related_chars = set()

        # 檢查是否為獨體字
        is_independent_char = "獨體字" in sisters
        if is_independent_char:
            display_lines.append(display_char)

        # 顯示同字根（獨體字跳過此部分）
        if not is_independent_char:
            for positions, chars in sisters.get("結構相同部件同位", {}).items():
                # 套用顏色篩選（透過 adapter）
                filtered_chars = chars
                if hasattr(self, 'filter_colors') and len(self.filter_colors) > 0:
                    font = self.adapter.get_current_font()
                    filtered_chars = self.adapter.filter_by_color(
                        filtered_chars,
                        font,
                        self.filter_colors
                    )

                if filtered_chars:
                    display_lines.append(f"{positions} {''.join(filtered_chars)}")
                    related_chars.update(filtered_chars)

        # 檢查是否啟用衍生字顯示
        if self.show_derived:
            derived_groups = self.core.find_derived_characters(display_char, charset)
            if derived_groups:
                # 先加入分隔線
                if display_lines:
                    display_lines.append("-" * 3)

                # 過濾並加入衍生字結果
                for component, chars in derived_groups.items():
                    # 過濾掉已在關聯字中的字符
                    filtered_chars = [c for c in chars if c not in related_chars]

                    # 套用顏色篩選（透過 adapter）
                    if hasattr(self, 'filter_colors') and len(self.filter_colors) > 0:
                        font = self.adapter.get_current_font()
                        filtered_chars = self.adapter.filter_by_color(
                            filtered_chars,
                            font,
                            self.filter_colors
                        )

                    if filtered_chars:
                        display_lines.append(f"{component} {''.join(filtered_chars)}")

        display_text = '\n'.join(display_lines) if display_lines else display_char
        # 清理可能造成顯示問題的字符
        display_text = self.core.clean_display_text(display_text)

        # 使用動態字型的 NSAttributedString（右側區域啟用加大字距和行距）
        attr_string = self.create_attributed_string(
            display_text, RELATED_CHARS_FONT_SIZE, use_enhanced_spacing=True
        )
        text_view = self.w.relatedChars.getNSTextView()
        text_view.textStorage().setAttributedString_(attr_string)

    # === 預覽功能 ===

    def update_preview(self, char):
        """更新字符預覽（水平垂直居中）"""
        font = self.get_font_for_char(char)

        # 垂直偏移量：負值向下移動，正值向上移動
        # 微調讓文字在 90px 高度區域內視覺居中
        baseline_offset = -4

        # 段落樣式：水平居中
        paragraph_style = NSMutableParagraphStyle.alloc().init()
        paragraph_style.setAlignment_(1)  # NSCenterTextAlignment = 1

        # 使用系統語義顏色，自動適應深淺模式
        preview_text = NSAttributedString.alloc().initWithString_attributes_(
            char,
            {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: NSColor.labelColor(),
                NSBaselineOffsetAttributeName: baseline_offset,
                NSParagraphStyleAttributeName: paragraph_style
            }
        )
        self.w.preview.set(preview_text)

    def get_font_for_char(self, char, size=72):
        """
        使用 macOS 原生 CTFontCreateForString 自動選擇字型

        讓系統自動從 cascade list 尋找能顯示該字符的字型，
        無需硬編碼特定字型家族，支援不同區域使用者的系統字型。

        參數:
            char: 要顯示的字符
            size: 字型大小（預設 72pt）

        回傳:
            NSFont: 能顯示該字符的字型
        """
        if not char:
            return NSFont.systemFontOfSize_(size)

        # 查詢快取
        cache_key = (char, size)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        try:
            # 建立基礎 CTFont（系統 UI 字型包含完整的 cascade list）
            base_ct_font = CoreText.CTFontCreateWithName(
                ".AppleSystemUIFont",
                size,
                None
            )

            # 使用 CTFontCreateForString 尋找能顯示該字符的字型
            # range: (location, length)
            fallback_ct_font = CoreText.CTFontCreateForString(
                base_ct_font,
                char,
                (0, len(char))
            )

            # 釋放 base_ct_font（不再需要，避免記憶體洩漏）
            del base_ct_font

            # 取得 fallback 字型的 PostScript 名稱
            ps_name = CoreText.CTFontCopyPostScriptName(fallback_ct_font)

            # 檢查是否為 LastResort 字型（表示系統找不到適合的字型）
            is_last_resort = ps_name and "LastResort" in str(ps_name)

            # 釋放 ps_name（不再需要）
            del ps_name

            if is_last_resort:
                # 釋放 fallback_ct_font（不使用，改用系統字型）
                del fallback_ct_font
                font = NSFont.systemFontOfSize_(size)
            else:
                # CTFont 和 NSFont 可透過 toll-free bridging 互轉
                font = fallback_ct_font

            # 快取管理：超過上限時清除一半
            if len(self._font_cache) >= self._CACHE_MAX_SIZE:
                keys_to_remove = list(self._font_cache.keys())[:self._CACHE_MAX_SIZE // 2]
                for key in keys_to_remove:
                    del self._font_cache[key]

            # 快取結果
            self._font_cache[cache_key] = font
            return font

        except Exception:
            # 發生錯誤時 fallback 到系統字型
            return NSFont.systemFontOfSize_(size)

    def create_attributed_string(self, text, size, use_enhanced_spacing=False):
        """
        建立帶有動態字型和顏色的 NSAttributedString

        為文字中的每個漢字字符自動選擇適當的字型（使用 CTFontCreateForString），
        非漢字字符使用系統字型。使用系統語義顏色支援深淺模式。

        參數:
            text: 要顯示的文字
            size: 字型大小
            use_enhanced_spacing: 是否使用加大的字距和行距（用於右側相關字區域）

        回傳:
            NSAttributedString: 帶有正確字型和顏色的富文本
        """
        if not text:
            return NSAttributedString.alloc().initWithString_("")

        result = NSMutableAttributedString.alloc().init()
        system_font = NSFont.systemFontOfSize_(size)
        # 使用系統語義顏色，自動適應深淺模式
        text_color = NSColor.labelColor()

        # 建立段落樣式（用於行距）
        paragraph_style = None
        if use_enhanced_spacing:
            paragraph_style = NSMutableParagraphStyle.alloc().init()
            # 設定行距：行高 = 字體大小 × 行高倍數
            line_height = size * RELATED_CHARS_LINE_HEIGHT
            paragraph_style.setMinimumLineHeight_(line_height)
            paragraph_style.setMaximumLineHeight_(line_height)

        for char in text:
            code_point = ord(char)
            # 為 CJK 相關字符使用 TW-Sung 字型
            # 包含完整的 CJK 區塊以確保一致性
            is_cjk_related = (
                0x2E80 <= code_point <= 0x2EFF or   # CJK Radicals Supplement（部首補充）
                0x2F00 <= code_point <= 0x2FDF or   # Kangxi Radicals（康熙部首）
                0x2FF0 <= code_point <= 0x2FFF or   # IDC（表意文字描述字符 ⿰⿱⿲）
                0x3400 <= code_point <= 0x4DBF or   # CJK Extension A
                0x4E00 <= code_point <= 0x9FFF or   # CJK Unified Ideographs
                0xF900 <= code_point <= 0xFAFF or   # CJK Compatibility Ideographs
                code_point >= 0x20000               # CJK Extension B-H+
            )
            if is_cjk_related:
                font = self.get_font_for_char(char, size)
            else:
                font = system_font

            # 建立屬性字典
            attributes = {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: text_color
            }

            # 加入字距和行距（僅用於右側相關字區域）
            if use_enhanced_spacing:
                attributes[NSKernAttributeName] = RELATED_CHARS_KERN
                if paragraph_style:
                    attributes[NSParagraphStyleAttributeName] = paragraph_style

            char_attr = NSAttributedString.alloc().initWithString_attributes_(
                char, attributes
            )
            result.appendAttributedString_(char_attr)

        return result

    # === 插入按鈕功能 ===

    def setup_selection_observer(self):
        """監聽右側相關字區域的選取變化，控制插入按鈕啟用狀態"""
        textView = self.w.relatedChars.getNSTextView()
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self.selectionObserver,
            "textViewSelectionDidChange:",
            "NSTextViewDidChangeSelectionNotification",
            textView
        )

    def on_selection_changed(self, notification):
        """當選取變化時更新插入按鈕狀態"""
        textView = self.w.relatedChars.getNSTextView()
        has_selection = textView.selectedRange().length > 0
        self.w.insertButton.enable(has_selection)

    def insert_selected_text(self, sender):
        """將選取的文字插入到編輯分頁"""
        textView = self.w.relatedChars.getNSTextView()
        selectedRange = textView.selectedRange()
        if selectedRange.length == 0:
            return
        selectedText = textView.string().substringWithRange_(selectedRange)
        selectedText = str(selectedText).strip()
        if selectedText:
            font = self.adapter.get_current_font()
            self.adapter.insert_to_tab(font, selectedText)

    # === 全字庫連結 ===

    def open_cns_link(self, sender):
        """在瀏覽器開啟當前字符的全字庫頁面"""
        if not self.current_char:
            return

        unicode_hex = format(ord(self.current_char), 'X')

        # 根據 Glyphs 介面語言決定全字庫語言
        # la=0 中文版（繁中/簡中/日文）, la=1 英文版（其他語言）
        try:
            from GlyphsApp import Glyphs
            glyphs_lang = Glyphs.defaults.get("AppleLanguages", ["en"])[0]
            # 中日文使用者使用中文版，其他使用英文版
            la = 0 if glyphs_lang.startswith("zh") or glyphs_lang.startswith("ja") else 1
        except Exception:
            la = 1  # fallback 使用英文版

        url = f"https://www.cns11643.gov.tw/searchQ.jsp?WORD={unicode_hex}&la={la}"

        import webbrowser
        webbrowser.open(url)

    # === 其他功能 ===

    def windowWillClose(self, sender):
        """
        視窗關閉時的清理方法

        參數:
        sender: 視窗物件
        """
        # 移除選取變化監聽
        try:
            NSNotificationCenter.defaultCenter().removeObserver_(self.selectionObserver)
        except Exception:
            pass

        # 移除 Glyphs 回調（透過 adapter）
        try:
            self.adapter.unregister_callback(self.on_glyph_changed)
        except Exception:
            pass


# 作為腳本獨立執行時建立實例
if __name__ == "__main__":
    HanziComponentSearchTool()
