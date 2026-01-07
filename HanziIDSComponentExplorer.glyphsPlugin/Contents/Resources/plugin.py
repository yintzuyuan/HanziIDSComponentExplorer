# encoding: utf-8

###########################################################################################################
#
#   Hanzi IDS Component Explorer
#   A Glyphs plugin for exploring Chinese character components using IDS (Ideographic Description Sequences)
#
#   Copyright (c) 2026 TzuYuan Yin
#   https://github.com/yintzuyuan
#
###########################################################################################################

from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import Glyphs, WINDOW_MENU
from GlyphsApp.plugins import GeneralPlugin


class HanziIDSComponentExplorer(GeneralPlugin):
    """漢字 IDS 部件查詢外掛"""

    @objc.python_method
    def settings(self):
        """初始化設定 - 外掛載入時呼叫一次"""
        self.name = Glyphs.localize({
            'en': 'Hanzi IDS Component Explorer',
            'zh-Hant': '漢字IDS部件查詢',
            'zh-Hans': '汉字IDS部件查询',
            'ja': '漢字IDS部品検索',
        })
        self.tool = None  # 延遲初始化

    @objc.python_method
    def start(self):
        """外掛啟動時呼叫 - 建立選單項目"""
        # Glyphs 3.3+ 新式寫法
        if Glyphs.buildNumber >= 3320:
            from GlyphsApp.UI import MenuItem
            newMenuItem = MenuItem(self.name, action=self.showWindow_, target=self)
        else:
            # 舊式寫法（向後相容）
            from AppKit import NSMenuItem
            newMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                self.name, self.showWindow_, ""
            )
            newMenuItem.setTarget_(self)

        Glyphs.menu[WINDOW_MENU].append(newMenuItem)

    def showWindow_(self, sender):
        """顯示或建立視窗（選單動作觸發）"""
        if self.tool is None or self.tool.w._window is None:
            # 延遲載入 UI 模組，或視窗已關閉需重建
            from glyphs_ui import HanziComponentSearchTool
            self.tool = HanziComponentSearchTool(title=self.name)
        else:
            # 視窗已存在，帶到前景
            self.tool.w.show()

    @objc.python_method
    def __file__(self):
        """保持不變"""
        return __file__
