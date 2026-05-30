# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-05-30

### Added

- **右欄重組為「子部件同位 → --- → 含本字組合」** — 取代既有同字根（sister）3 層渲染、改用 IDC + 位置標籤統一風格：
  - **上半「子部件同位」**：對複合字 display_char 頂層 IDS 每個 Unicode operand 位置 N、列「`{IDC}{N}` <chars>」、chars 為該位置含同部件的字。例如搜「明」（=⿰日月）→ `⿰1 暉暗暝 …`（日同位）+ `⿰2 朋朗期 …`（月同位）
  - **下半「含本字組合」**：列含 display_char 作為部件的字、按頂層 IDC 位置細分。例如搜「金」→ `⿰1 鐘鈴銀 …`、`⿰≡ 鍂`、`⿱≡· 鑫𨰻 …`
  - **`---` 分隔**：條件式、只在上下都有實際內容才插
  - **葉部件搜尋**（如「金」）上半自動空、整段就是下半的位置細分
- **位置標籤完整語法**：
  - `{IDC}{N}`（如 `⿰1`、`⿱2`、`⿲3`）：query 在 c 的頂層位置 N、直接是該 operand
  - `{IDC}≡`：多個位置都直接含 query（對稱、如 鍂=⿰金金 對搜「金」歸 `⿰≡`）
  - `{IDC}{N}·` / `{IDC}≡·`：嵌套標 `·`（U+00B7）。query 不直接是位置 N 的 operand、而是嵌在子結構或子字內。例如搜「明」、`⿰1· 鴠`（鴠=⿰旦鳥、日嵌在旦內）；搜「金」、`⿱≡· 鑫`（鑫=⿱金鍂、位置 1 直接金、位置 2 嵌套含金）
  - 同位置 direct 排在 nested 前（`⿰1` 在 `⿰1·` 前）
  - 對稱字（如 林=⿰木木）位置 1、2 各自獨立一行、不合併 `⿰≡`
- **多部件交集粗略分組** — 搜 2+ 部件（如「金童」）右欄交集按頂層 IDC 字元分組（`⿰ 鐘 …`），不細分位置（多部件位置維度爆炸故簡化）
- **嵌套位置可推斷** — 查詢部件嵌在頂層子部件內仍歸到「該子部件所在的頂層位置」。例如搜「立」→ 鐘=⿰金童 歸 `⿰2`（立 嵌在童裡、童在 ⿰2）

### Changed (breaking)

- **移除同字根（sister）3 層分類渲染** — 既有「結構相同部件同位」「結構部件相同」「部件相同」整段從右欄消失。「結構相同部件同位」第一層的同位資訊由新「子部件同位」上半取代（label 改為 IDC + 位置）；後兩層「結構同/部件同但不同位」的字需透過中欄點該部件切視角取得（既有中欄機制不受影響、`find_sister_characters` core method 保留以備他用）

### Internal

- 新增 `HanziCore` methods：`classify_by_position(char, query, granularity)`、`format_position_label(idc, pos, is_nested)`、`group_by_position(chars, query, granularity)`、`compose_immediate_component_lines(derived_groups, display_char)`、`_top_position_contains(c, target_idc, target_position, query)`、`_operand_directly_is(operand_tokens, query_set)`、`_operand_contains(operand_tokens, query_set)`；複用既有 `_recursive_components()` 判斷頂層 operand 是否含查詢部件
- `update_related_display` 簡化為 upper/lower 兩段組裝；新增 UI helper `_apply_chars_filters` 封裝「排除已列字 + 顏色 + 筆畫」三道篩選
- 模組常數新增：`IDC_ARITY`（每個 IDC 的 operand 個數、含 〾 = 1）、`IDC_ORDER`（分組展示順序）、`MULTI_POSITION_MARKER`（`≡`，U+2261）、`NESTED_POSITION_MARKER`（`·`，U+00B7）、`UNCLASSIFIED_LABEL`（`∅`，獨體字 fallback）
- IDS 解析輔助：module-level `_split_top_operands(tokens)`、`_skip_one_operand(tokens, pos)`

## [1.1.1] - 2026-05-28

### Fixed

- **多部件搜尋可比對中間部件** — 修正多部件搜尋只比對「展開後的葉部件」，導致本身可再拆的中間部件無法當查詢詞的問題。現在「立里」找得到「童」（童=⿱立里）、「金童」找得到「鐘」（鐘=⿰金童）、「火林」找得到「焚」（焚=⿱林火）。原本「火木木」這類葉部件查詢不受影響

### Internal

- 將 `search_all` 使用的葉部件反向索引改為「全層級節點」反向索引：`_recursive_components`（拆解樹每個節點各計數一次，含中間部件與葉部件）、`_ensure_recursive_index`（取代 `_leaf_*` 系列）。對僅含原子部件的查詢，計數結果與舊葉索引完全相同（零回歸）

## [1.1.0] - 2026-05-27

### Added

- **多部件組合搜尋** — 搜尋欄輸入多個漢字部件（如「氵木」）即搜尋「同時包含所有部件」的字。採遞迴比對：部件藏在更深層也算（如「淋」=⿰氵林，木在林裡仍算含木）；重複部件代表「至少 N 個」（如「木木」找含兩個以上木的字）
- **多部件模式呈現** — 中欄列出輸入部件（首行為原始輸入，可點選切換「交集」與「單部件衍生字」視角）、右欄列出交集結果、左欄初始空白待點選某字才填
- **多部件自動鎖定** — 進入多部件模式時自動勾選並鎖定「衍生字」與「深度拆解」開關（多部件本質為遞迴衍生字邏輯），離開時恢復原設定
- **多部件筆畫篩選** — 筆畫滑桿在多部件模式以「各輸入部件筆畫數加總」為基準篩選交集結果（如「氵木」= 3+4 = 7 畫）

### Internal

- 新增 `search_all`（遞迴展開至葉部件 + 多重集計數包含）、`filter_by_stroke_value`（數值基準筆畫篩選，`filter_by_strokes` 重用之），以及 lazy 葉部件反向索引（首次建立後快取）

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

[1.2.0]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.2.0
[1.1.1]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.1.1
[1.1.0]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.1.0
[1.0.3]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.0.3
[1.0.2]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.0.2
[1.0.0]: https://github.com/yintzuyuan/HanziIDSComponentExplorer/releases/tag/v1.0.0
