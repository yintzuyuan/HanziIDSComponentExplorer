# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-04-11

### Added

- **筆畫數篩選滑桿** - 主視窗底部新增離散滑桿（±0/±1/±2/±3/±5/關閉），依與當前主字的筆畫差篩選右側相關字面板（同字根、衍生字）
- **滑桿狀態常駐顯示** - 滑桿右側以 inline 文字常駐顯示當前值（±N 或關閉），不需 hover tooltip
- **筆畫資料來源** - 自 CNS11643-OpenData 的 `Tables/Properties/CNS_stroke.txt` 載入並編譯進 `ids.pdata`
- **跨 session 設定持久化** - 筆畫篩選 tick 位置會記住，下次開啟外掛時自動套用

### Data

- 字符數量：102,956 個（自動從上游 CHISE IDS 更新）
- 筆畫資料覆蓋：76,983 個字符（74.8%）— 來自 CNS11643
- `ids.pdata` 紀錄結構新增 `strokes` 欄位（int 或 None）；舊版資料庫向後相容
- 超出 CNS11643 範圍的 Ext-G/H 罕字筆畫為 None；開啟篩選時這些字會被隱藏，僅在「關閉」時顯示

## [1.0.2] - 2026-03-15

### Improved

- **搜尋效能優化** - 預建反向索引，搜尋從 O(n) 遍歷降為 O(1) 查表
- **NFKC 正規化** - 限制正規化範圍為 CJK 相關區塊（康熙部首、CJK 相容字），避免圓圈數字等被誤正規化
- **清除假雙拆法** - 正規化 IDS 字串後，清除 210 個僅因 Unicode 編碼變體造成的重複拆法

### Data

- 多拆法字符：5,942 個（原 6,152 個，清除 210 個假雙拆法）

## [1.0.0] - 2026-01-07

### Added

- **部件搜尋功能** - 輸入部件找出包含該部件的所有字符
- **字符樹狀拆解** - 視覺化顯示漢字的組成結構
- **同字根查詢** - 找出相同結構和部件的關聯字
- **衍生字搜尋** - 顯示包含指定字符作為部件的所有衍生字
- **顏色標籤篩選** - 支援 Glyphs 顏色標籤篩選功能
- **自定義字符集** - 支援字型檔或自定義字符集檔案
- **多種 IDS 拆法** - 6.24% 字符（6,152 個）支援多種拆解方式
- **多 Unicode 值支援** - 完整收集相容字符和異體字映射
- **UI 本地化** - 支援繁體中文、簡體中文、英文介面
- **全字庫連結** - 一鍵查詢 CNS11643 全字庫資料
- **自動字型 Fallback** - 使用 CTFontCreateForString 實現缺字自動替換
- **IME 輸入偵測** - 避免輸入法輸入過程中頻繁重繪

### Architecture

- **三層架構設計**：核心邏輯層（hanzi_core.py）、Glyphs 適配層（glyphs_adapter.py）、UI 層（glyphs_ui.py）
- 核心邏輯層完全獨立，可在任何 Python 環境使用
- 嚴格的單向依賴，便於維護和擴展

### Data

- IDS 資料來源：[CHISE IDS database](https://www.chise.org/ids/)
- 字符數量：98,662 個
- 多拆法字符：6,152 個（6.24%）

[1.0.3]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.0.3
[1.0.2]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.0.2
[1.0.0]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.0.0
