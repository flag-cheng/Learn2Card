# Agent B PRD：Web 翻卡介面

## 使命
提供簡單 Web 介面載入 Agent A 的 JSON 輸出，支援分頁/序列翻卡、主題瀏覽與統計展示，作為示範用的可視化大綱。

## 技術棧與環境
> 📋 **請參閱**：技術棧與環境設定的完整規範請參考 `.cursor/rules/frontend-rule.mdc`

⚠️ **重要**：本專案已有前端基礎架構，必須在現有專案上擴充，不得重新建立專案。

- **專案位置**：`frontend/` 目錄
- **技術棧**：React 18 + TypeScript + Vite 5
- **套件管理**：npm
- **現有基礎**：已實作卡片瀏覽介面（`src/App.tsx`），需在此基礎上擴充

## 準備工作（實作前必須完成）
在開始實作 Agent B 之前，必須先完成以下準備：

1. **建立 `frontend/public/` 目錄**（若不存在）
2. **轉存範例資料**：將 `frontend/src/sampleDeck.ts` 的 `sampleDeck` 物件轉存為 `frontend/public/deck.json`
   - 格式：標準 JSON（非 TypeScript）
   - 編碼：UTF-8（無 BOM）
   - 內容：與 `sampleDeck` 物件完全相同的資料結構
3. **修改資料載入邏輯**：Frontend 改從 `fetch('/deck.json')` 讀取資料，而非直接 import `sampleDeck.ts`

完成這些準備後，再開始實作檔案上傳和 Backend 呼叫功能。

## Backend 整合方式（與 Agent A 對接）
> 📋 **詳細技術規範請參閱**：`technical-spec.md` - "Agent B：Frontend 整合規範" 章節

### 簡要說明（採用方案 A：簡易 Demo 版）

**資料流程**：
```
使用者上傳檔案 
  ↓
Frontend 讀取內容（純文字）
  ↓
Frontend 產生可執行指令：cd backend && uv run python main.py --text "..."
  ↓
使用者複製指令並手動到終端執行
  ↓
Backend 執行完成，更新 frontend/public/deck.json
  ↓
使用者點擊「重新載入卡片」按鈕
  ↓
Frontend 重新 fetch('/deck.json') 並顯示新卡片
```

**為什麼採用方案 A**：
- ✅ 瀏覽器無法直接執行系統指令
- ✅ 避免建立額外的 HTTP API server（會大幅增加複雜度）
- ✅ 保持簡單，符合 Demo 用途
- ✅ 兩個 Agent 可以獨立開發，不需要額外的 API 協調

> 📋 **完整資料流、技術細節（字元跳脫、路徑處理等）請參閱**：`technical-spec.md` - "資料流程" 和 "技術細節" 章節

## 功能需求

### 1. 資料載入
- 從 `public/deck.json` 讀取卡片資料（使用 `fetch('/deck.json')`）
- 初始載入時顯示範例卡片
- 載入失敗時顯示錯誤提示

### 2. 檔案輸入（嚴格限制）
- **檔案上傳**：只接受 `.txt` 和 `.md` 格式
  - 使用 `<input type="file" accept=".txt,.md">`
  - 使用 FileReader API 讀取為純文字字串（UTF-8）
  - 檔案格式驗證：非 txt/md 顯示錯誤訊息
- **文字輸入**：提供多行文字輸入框，讓使用者直接貼上純文字內容
- **不得**提供 URL 輸入欄位或網頁抓取功能

### 3. Backend 指令產生
- 將使用者輸入的文字進行跳脫處理（處理引號、換行、特殊字元）
- 產生可執行的 Backend 指令：
  ```bash
  cd backend && uv run python main.py --text "使用者的文字"
  ```
- 顯示在畫面上供使用者查看

### 4. 複製與執行提示
- 提供「複製指令」按鈕，點擊後複製到剪貼簿
- 顯示明確的操作步驟：
  1. 點擊「複製指令」
  2. 開啟終端
  3. 貼上並執行指令
  4. 執行完成後，點擊下方「重新載入卡片」按鈕

### 5. 重新載入功能
- 提供「重新載入卡片」按鈕
- 點擊後重新執行 `fetch('/deck.json')`
- 解析 JSON 並更新顯示
- 顯示載入中狀態

### 6. 卡片瀏覽
- 上一張/下一張按鈕
- 分頁或序列瀏覽模式
- 鍵盤左右鍵快捷操作

### 7. 統計展示
- 同步顯示段落/主題/卡片數（使用 `stats.paragraphCount`、`stats.topicCount`、`stats.cardCount`）

### 8. 主題跳轉
- 依 topic 過濾/跳轉卡片
- 顯示主題標題

### 9. 錯誤處理
- 檔案格式驗證：若上傳非 txt/md 檔案，顯示明確錯誤訊息
- JSON schema 驗證：載入的 JSON 格式錯誤時提供可讀提示
- 空內容處理：文字為空或無效時的友善提示
- Fetch 失敗處理：檔案不存在時的提示

### 10. UI 設計
- 簡潔、可讀，行高、對比度足夠
- 適合 Windows 桌面瀏覽器（Chrome/Edge）

> 📋 **實作細節**：FileReader API 使用方式、字元跳脫處理、剪貼簿 API 等技術細節請參閱 `technical-spec.md` - "Agent B：Frontend 整合規範" 和 "技術細節" 章節

## 非功能需求（品質與效能要求）
> 💡 **說明**：「非功能需求」指的不是具體功能，而是系統的品質、效能、相容性等要求。

- **瀏覽器相容性**：優先支援 Chrome/Edge 桌面版，在 Windows 環境下正常運作
- **部署方式**：使用 Vite 的開發伺服器（`npm run dev`），或打包成靜態檔案（`npm run build`）
- **回應速度**：載入狀態要有明確提示，避免無回應狀態
- **錯誤處理**：任何錯誤（檔案格式、JSON 解析、fetch 失敗等）都要有清楚的使用者提示
- **程式碼品質**：使用 TypeScript 型別檢查，確保型別安全

## 實作指引與限制
> 📋 **請參閱**：通用 Frontend 開發規則請參考 `.cursor/rules/frontend-rule.mdc`

### 本模組特定限制

#### 必須遵守
- **輸入格式**：只接受 `.txt` 和 `.md` 檔案上傳，或純文字貼上
- **檔案驗證**：上傳時檢查副檔名，非 txt/md 要明確拒絕並顯示錯誤訊息
- **檔案讀取**：使用 FileReader API 讀取 `.txt` 或 `.md` 檔案內容為純文字字串
- **文字處理**：將純文字字串用於產生 Backend 執行指令（需跳脫特殊字元）
- **資料來源**：從 `public/deck.json` 載入卡片資料，**不從** `sampleDeck.ts` 讀取
- **初始資料**：專案初始化時，需將 `sampleDeck.ts` 的範例資料轉存為 `public/deck.json`
- **UI 元件**：使用 `<input type="file" accept=".txt,.md">` 限制檔案選擇器

#### 不得實作
- ❌ 不得提供 URL 輸入欄位
- ❌ 不得實作網頁抓取、爬蟲或任何 URL 內容讀取功能
- ❌ 不得支援 PDF、DOCX、HTML 等其他檔案格式（僅限 txt/md）
- ❌ 不得從 `sampleDeck.ts` 動態讀取資料（應從 `public/deck.json` 讀取）
- ❌ 不得在前端直接處理文字分析邏輯（必須透過 Backend 處理）
- ❌ **不得嘗試在瀏覽器中執行系統指令**（如 child_process、exec 等，瀏覽器做不到）
- ❌ **不得實作 HTTP API 呼叫或 server**（除非明確要求方案 B，目前採用方案 A）
- ❌ 不得使用 WebSocket、Server-Sent Events 等複雜的即時通訊（保持簡單）

## 驗收標準

> 📋 **詳細驗收標準請參閱**：`technical-spec.md` - "Agent B 驗收（M3）" 章節

### 基本功能
- ✅ `frontend/public/deck.json` 已存在（從 `sampleDeck.ts` 轉存）
- ✅ Frontend 從 `public/deck.json` 載入資料，**不從** `sampleDeck.ts` 讀取
- ✅ 頁面載入時顯示預設範例卡片
- ✅ 卡片瀏覽、統計、主題跳轉功能正常

### 檔案處理
- ✅ 能上傳 `.txt` 或 `.md` 檔案，成功讀取檔案內容為純文字字串
- ✅ 能在文字框貼上純文字內容
- ✅ 上傳非 txt/md 檔案時，顯示明確的格式錯誤提示

### Backend 整合
- ✅ 能產生正確的 Backend 執行指令（含跳脫字元處理）
- ✅ 「複製指令」按鈕能將指令複製到剪貼簿
- ✅ 顯示明確的執行步驟提示
- ✅ 「重新載入卡片」按鈕能重新 `fetch('/deck.json')` 並更新顯示

### 整合測試
- ✅ 完整流程測試：
  1. 上傳測試檔案 → 產生指令
  2. 複製指令 → 手動執行 Backend
  3. 點擊重新載入 → 顯示新卡片
  4. 整個流程能順利完成，新卡片正確顯示

### 錯誤處理
- ✅ 各種異常情況都有清楚的使用者提示
- ✅ **確認無 URL 輸入欄位**，不支援網頁抓取功能
- ✅ **確認無 HTTP API 呼叫或系統指令執行**（採用簡易方案 A）

> 📋 **更多測試案例**：邊界條件、錯誤處理、瀏覽器相容性測試請參閱 `technical-spec.md`

## 風險與緩解
- **JSON 版本差異**：固定 schema，必要時增加向後相容映射
- **大檔渲染**：使用分頁/虛擬列表策略，顯示 loading
- **瀏覽器差異**：優先桌面 Chrome/Edge，明確標示支援範圍
- **字元跳脫問題**：完整測試特殊字元（引號、換行、反斜線等）的處理

## 與其他模組的關係
- **資料來源**：從 Agent A 產生的 `public/deck.json` 讀取資料
- **輸入處理**：讀取檔案內容後，產生指令供使用者執行 Agent A
- **整合方式**：不直接呼叫 Agent A，而是產生指令讓使用者手動執行

> 📋 **整合流程詳見**：`docs/prd/global.md` - "整合任務" 章節
