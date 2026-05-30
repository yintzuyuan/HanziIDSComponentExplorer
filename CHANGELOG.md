# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Language note**: From v1.2.0 onwards, CHANGELOG entries are written in English for international readers. Earlier entries (v1.0.x ~ v1.1.x) remain in Traditional Chinese.

## [1.2.0] - 2026-05-30

### Added

- **Right panel redesigned as "Sub-component co-position → `---` → Containing-self compositions"** — Replaces the previous three-tier sister-character rendering with a unified IDC + position label style:
  - **Upper section "Sub-component co-position"**: For each Unicode operand at position N in the top-level IDS of a compound `display_char`, output one line `{IDC}{N} <chars>` where chars are characters that have the same component at the same top-level position. Example: searching 明 (`⿰日月`) → `⿰1 暉暗暝 …` (日 co-positioned at `⿰1`) + `⿰2 朋朗期 …` (月 co-positioned at `⿰2`)
  - **Lower section "Containing-self compositions"**: Lists characters that use `display_char` as a component, grouped by top-level IDC position. Example: searching 金 → `⿰1 鐘鈴銀 …`, `⿰≡ 鍂`, `⿱≡· 鑫𨰻 …`
  - **`---` separator**: Conditional — inserted only when both upper and lower sections have actual content
  - **Leaf component search** (e.g., 金): upper section is automatically empty; the entire panel is the lower section's position-grouped breakdown
- **Complete position label syntax**:
  - `{IDC}{N}` (e.g., `⿰1`, `⿱2`, `⿲3`): query is the direct operand at top-level position N of c
  - `{IDC}≡`: multiple positions directly contain the query (symmetric — e.g., 鍂=`⿰金金` → `⿰≡` when searching 金)
  - `{IDC}{N}·` / `{IDC}≡·`: nested suffix `·` (U+00B7). Query is not directly the operand at position N, but is nested inside a substructure or sub-character. Examples: searching 明 → `⿰1· 鴠` (鴠=`⿰旦鳥`, 日 nested inside 旦); searching 金 → `⿱≡· 鑫` (鑫=`⿱金鍂`, position 1 direct, position 2 nested via 鍂)
  - Same position: direct rows come before nested rows (`⿰1` before `⿰1·`)
  - Symmetric characters (e.g., 林=`⿰木木`): positions 1 and 2 each get their own row, not merged into `⿰≡`
- **Multi-component intersection coarse grouping** — Searching 2+ components (e.g., 金童), the intersection groups by top-level IDC character (`⿰ 鐘 …`) without sub-position breakdown (position dimensions explode with multi-component queries, so coarse grouping keeps results readable)
- **Nested position inferred** — When the query is nested inside a top-level sub-component, it's still attributed to "the position where that sub-component lives". Example: searching 立 → 鐘=`⿰金童` is grouped under `⿰2` (because 立 is nested inside 童, which lives at `⿰2`)

### Changed (breaking)

- **Removed sister three-tier rendering** — The existing tiers "結構相同部件同位" (same structure, same component at same position), "結構部件相同" (same structure, same component), and "部件相同" (same component) are removed from the right panel. The first tier's co-position information is replaced by the new "Sub-component co-position" upper section (label style changed to IDC + position). Characters from the latter two tiers ("same structure / same component but different position") are now accessed by clicking the component in the middle column to switch perspective (existing middle-column switching unaffected; `find_sister_characters` core method preserved for potential future use)

### Internal

- New `HanziCore` methods: `classify_by_position(char, query, granularity)`, `format_position_label(idc, pos, is_nested)`, `group_by_position(chars, query, granularity)`, `compose_immediate_component_lines(derived_groups, display_char)`, `_top_position_contains(c, target_idc, target_position, query)`, `_operand_directly_is(operand_tokens, query_set)`, `_operand_contains(operand_tokens, query_set)`; reuses existing `_recursive_components()` to check whether a top-level operand contains the query
- `update_related_display` simplified to upper/lower two-section assembly; new UI helper `_apply_chars_filters` encapsulates the three filters (already-listed exclusion + color + stroke)
- New module-level helper `resolve_display_char(char, sticky, current)` resolves which character to display in the right panel (explicit > sticky > current_char), fixing the sub-component view stroke-filter regression where switching filters reverted the panel back to the base character
- New module constants: `IDC_ARITY` (operand count per IDC, including 〾=1), `IDC_ORDER` (group display order), `MULTI_POSITION_MARKER` (`≡`, U+2261), `NESTED_POSITION_MARKER` (`·`, U+00B7), `UNCLASSIFIED_LABEL` (`∅`, leaf character fallback)
- IDS parsing helpers: module-level `_split_top_operands(tokens)`, `_skip_one_operand(tokens, pos)`

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
