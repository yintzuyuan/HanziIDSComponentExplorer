# encoding: utf-8
"""
Hanzi Component Explorer - 本地化字串模組

提供 UI 介面多語言支援，使用 Glyphs.localize() API
支援語言：en, zh-Hant, zh-Hans, ja

© 2025 TzuYuan Yin
"""

from __future__ import division, print_function, unicode_literals

# 本地化字串字典
STRINGS = {
    # 視窗與標題
    "window_title": {
        "en": "Hanzi IDS Component Explorer",
        "zh-Hant": "漢字IDS部件查詢",
        "zh-Hans": "汉字IDS部件查询",
        "ja": "漢字IDS部品検索",
    },
    "search_placeholder": {
        "en": "Enter character or Unicode",
        "zh-Hant": "輸入漢字或 Unicode 編碼",
        "zh-Hans": "输入汉字或 Unicode 编码",
        "ja": "漢字または Unicode を入力",
    },
    # CheckBox
    "checkbox_deep_analysis": {
        "en": "Deep Analysis",
        "zh-Hant": "深度拆解",
        "zh-Hans": "深度拆解",
        "ja": "深層分解",
    },
    "checkbox_derived": {
        "en": "Derived",
        "zh-Hant": "衍生字",
        "zh-Hans": "衍生字",
        "ja": "派生字",
    },
    # 按鈕（參照 Glyphs 官方詞彙）
    "btn_select_all": {
        "en": "Select All",
        "zh-Hant": "全選",
        "zh-Hans": "全选",
        "ja": "すべてを選択",
    },
    "btn_clear": {
        "en": "Clear",
        "zh-Hant": "清除",
        "zh-Hans": "清除",
        "ja": "消去",
    },
    "btn_cancel": {
        "en": "Cancel",
        "zh-Hant": "取消",
        "zh-Hans": "取消",
        "ja": "キャンセル",
    },
    "btn_apply": {
        "en": "Apply",
        "zh-Hant": "套用",
        "zh-Hans": "应用",
        "ja": "適用",
    },
    # 下拉選單
    "charset_font": {
        "en": "Font File",
        "zh-Hant": "字型檔",
        "zh-Hans": "字体文件",
        "ja": "フォントファイル",
    },
    "charset_custom": {
        "en": "Custom Set...",
        "zh-Hant": "自訂字集...",
        "zh-Hans": "自定义字集...",
        "ja": "カスタムセット...",
    },
    # 顏色選擇器
    "color_picker_title": {
        "en": "Select Color",
        "zh-Hant": "選擇顏色",
        "zh-Hans": "选择颜色",
        "ja": "色を選択",
    },
    # 插入按鈕
    "btn_insert_tooltip": {
        "en": "Insert selected text in current tab",
        "zh-Hant": "將選取文字插入到目前分頁",
        "zh-Hans": "将选中文字插入到当前标签页",
        "ja": "選択テキストを現在のタブに挿入",
    },
    # 顏色篩選 Tooltip
    "tooltip_no_filter": {
        "en": "No color filter",
        "zh-Hant": "無顏色篩選",
        "zh-Hans": "无颜色筛选",
        "ja": "カラーフィルターなし",
    },
    "tooltip_filter_count": {
        "en": "{count} colors selected",
        "zh-Hant": "已選 {count} 個顏色",
        "zh-Hans": "已选 {count} 个颜色",
        "ja": "{count} 色選択中",
    },
    # 統一篩選選單
    "menu_color_filter": {
        "en": "Color Filter...",
        "zh-Hant": "顏色篩選...",
        "zh-Hans": "颜色筛选...",
        "ja": "カラーフィルター...",
    },
    "menu_color_filter_count": {
        "en": "Color Filter ({count})...",
        "zh-Hant": "顏色篩選 ({count})...",
        "zh-Hans": "颜色筛选 ({count})...",
        "ja": "カラーフィルター ({count})...",
    },
    # 筆畫數篩選滑桿
    "slider_stroke_label": {
        "en": "Strokes±",
        "zh-Hant": "筆畫±",
        "zh-Hans": "笔画±",
        "ja": "画数±",
    },
    "slider_stroke_off": {
        "en": "OFF",
        "zh-Hant": "關",
        "zh-Hans": "关",
        "ja": "OFF",
    },
    "tooltip_stroke_filter": {
        "en": "Filter related characters by stroke count difference from current character",
        "zh-Hant": "依與當前字的筆畫差篩選相關字",
        "zh-Hans": "依与当前字的笔画差筛选相关字",
        "ja": "現在の字との画数差で関連字をフィルター",
    },
    # 參考字型資料夾（#26）
    "menu_ref_fonts_empty": {
        "en": "Reference Fonts: None",
        "zh-Hant": "參考字型：無",
        "zh-Hans": "参考字体：无",
        "ja": "参照フォント：なし",
    },
    "menu_ref_fonts_count": {
        "en": "Reference Fonts: {count}",
        "zh-Hant": "參考字型：{count} 個檔案",
        "zh-Hans": "参考字体：{count} 个文件",
        "ja": "参照フォント：{count} 個",
    },
    "menu_open_ref_fonts_folder": {
        "en": "Open Reference Fonts Folder...",
        "zh-Hant": "開啟參考字型資料夾...",
        "zh-Hans": "打开参考字体文件夹...",
        "ja": "参照フォントフォルダを開く...",
    },
    "tooltip_display_font": {
        "en": "Display font: {name} ({source})",
        "zh-Hant": "顯示字型：{name}（{source}）",
        "zh-Hans": "显示字体：{name}（{source}）",
        "ja": "表示フォント：{name}（{source}）",
    },
    "font_source_folder": {
        "en": "reference folder",
        "zh-Hant": "參考資料夾",
        "zh-Hans": "参考文件夹",
        "ja": "参照フォルダ",
    },
    "font_source_family": {
        "en": "installed, matches current document",
        "zh-Hant": "已安裝・同當前文件",
        "zh-Hans": "已安装・同当前文件",
        "ja": "インストール済み・現在の書類と同名",
    },
    "font_source_covering": {
        "en": "installed",
        "zh-Hant": "已安裝",
        "zh-Hans": "已安装",
        "ja": "インストール済み",
    },
    "font_source_cascade": {
        "en": "system cascade",
        "zh-Hant": "系統自動選擇",
        "zh-Hans": "系统自动选择",
        "ja": "システム自動選択",
    },
    "font_source_system": {
        "en": "system font",
        "zh-Hant": "系統字型",
        "zh-Hans": "系统字体",
        "ja": "システムフォント",
    },
}


def L(key):
    """
    取得本地化字串

    參數:
        key (str): 字串鍵名

    回傳:
        str: 本地化後的字串，如果找不到則返回鍵名本身
    """
    try:
        from GlyphsApp import Glyphs

        return Glyphs.localize(STRINGS.get(key, {"en": key}))
    except Exception:
        # 測試環境 fallback：使用英文
        # 捕捉 ImportError 和 objc.nosuchclass_error 等
        return STRINGS.get(key, {"en": key}).get("en", key)


# === 測試程式碼 ===

if __name__ == "__main__":
    """測試本地化模組"""
    print("=== 本地化模組測試 ===\n")

    for key in STRINGS:
        value = L(key)
        print(f"{key}: {value}")

    print("\n=== 測試完成 ===")
