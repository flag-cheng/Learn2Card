# Agent B PRD：Web 翻卡介面（Frontend 專責）

## 職責範圍
**Agent B 僅負責 Frontend（前端介面）**：
- ✅ 提供 UI 讓使用者上傳檔案或輸入文字
- ✅ 提供 UI 讓使用者調整 Backend 參數
- ✅ 讀取檔案內容（使用 FileReader API）
- ✅ 透過 HTTP API 呼叫 Backend 處理文字
- ✅ 載入並顯示 `public/deck.json` 的卡片資料
- ✅ 提供卡片瀏覽、統計、主題跳轉功能
- ❌ **不負責** 文本分析邏輯（由 Agent A 處理）
- ❌ **不負責** 卡片生成演算法（由 Agent A 處理）

## 使命
提供簡單 Web 介面讓使用者輸入文字、調整參數、透過 HTTP API 觸發 Agent A（Backend）處理，並自動載入展示生成的卡片，支援分頁/序列翻卡、主題瀏覽與統計展示。

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

### 簡要說明（HTTP API 整合）

**資料流程**：
```
使用者上傳檔案或輸入文字
  ↓
Frontend 讀取內容（純文字）
  ↓
使用者調整參數（threshold, maxTopics, maxBullets 等）
  ↓
點擊「生成卡片」按鈕
  ↓
Frontend 透過 HTTP POST 呼叫 Backend API
  ↓
Backend 執行處理，更新 frontend/public/deck.json，回傳結果
  ↓
Frontend 自動重新載入並顯示新卡片
```

**整合方式說明**：
- ✅ Backend 提供 FastAPI HTTP API（`POST http://127.0.0.1:8000/api/process`）
- ✅ Frontend 透過 `fetch()` 直接呼叫 API，無需手動複製指令
- ✅ 使用者在 UI 中調整參數，點擊按鈕即可觸發處理
- ✅ 處理完成後自動更新顯示，使用者體驗流暢

> 📋 **完整資料流、API 規格、錯誤處理等技術細節請參閱**：`technical-spec.md` - "資料流程" 和 "Agent B：Frontend 整合規範" 章節

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

### 3. Backend 參數輸入介面
提供 UI 讓使用者調整 Backend 的處理參數（全部使用預設值也可以）：

- **分群閾值**（`topic_threshold`）：
  - 預設值：0.75
  - 範圍：0.0–1.0
  - UI：滑桿（slider）或數字輸入框
  - 說明：「相似度閾值，數值越高分群越細」
  
- **最大主題數**（`max_topics`）：
  - 預設值：5
  - 範圍：1–10
  - UI：數字輸入框或下拉選單
  - 說明：「最多產生幾個主題」
  
- **每卡摘要數**（`max_bullets`）：
  - 預設值：5
  - 範圍：1–5
  - UI：數字輸入框或下拉選單
  - 說明：「每張卡片最多幾個要點」
  
- **除錯模式**（`debug`）：
  - 預設值：false（不開啟）
  - UI：勾選框（checkbox）
  - 說明：「顯示詳細的處理資訊」

### 4. 生成卡片功能
- 提供「生成卡片」按鈕
- 點擊後：
  1. 顯示載入中狀態（spinner 或進度提示）
  2. 將文字內容和參數透過 HTTP POST 送到 Backend API
  3. 等待 Backend 處理完成
  4. 自動重新載入 `deck.json` 並更新顯示
  5. 顯示成功訊息（例如：「已成功產生 6 張卡片」）
- 錯誤處理：
  - Backend 未啟動：顯示「無法連接到 Backend，請確認 Backend 服務已啟動」
  - 處理失敗：顯示 Backend 回傳的錯誤訊息
  - 網路錯誤：顯示「網路連接失敗，請檢查網路狀態」

### 6. 卡片瀏覽
- 上一張/下一張按鈕
- 分頁或序列瀏覽模式
- 鍵盤左右鍵快捷操作

### 7. 統計展示
- 同步顯示段落/主題/卡片數（使用 `stats.paragraphCount`、`stats.topicCount`、`stats.cardCount`）

### 8. 主題跳轉
- 依 topic 過濾/跳轉卡片
- 顯示主題標題

### 5. 錯誤處理
- 檔案格式驗證：若上傳非 txt/md 檔案，顯示明確錯誤訊息
- JSON schema 驗證：載入的 JSON 格式錯誤時提供可讀提示
- 空內容處理：文字為空或無效時的友善提示
- API 連接失敗：Backend 未啟動或無法連接時的提示
- Backend 錯誤：顯示 Backend 回傳的錯誤訊息
- 參數驗證：若使用者輸入的參數超出範圍，顯示提示並使用預設值
- 網路逾時：處理請求超時的情況並提供重試選項

### 6. UI 設計
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
- **API 呼叫**：使用 `fetch()` API 透過 HTTP POST 將文字和參數傳送到 Backend
- **資料來源**：從 `public/deck.json` 載入卡片資料，**不從** `sampleDeck.ts` 讀取
- **初始資料**：專案初始化時，需將 `sampleDeck.ts` 的範例資料轉存為 `public/deck.json`
- **UI 元件**：使用 `<input type="file" accept=".txt,.md">` 限制檔案選擇器
- **API Endpoint**：使用 `POST http://127.0.0.1:8000/api/process`，Content-Type 為 `application/json`
- **錯誤顯示**：處理 HTTP 4xx/5xx 錯誤，顯示清楚的使用者訊息

#### 不得實作
- ❌ 不得提供 URL 輸入欄位
- ❌ 不得實作網頁抓取、爬蟲或任何 URL 內容讀取功能
- ❌ 不得支援 PDF、DOCX、HTML 等其他檔案格式（僅限 txt/md）
- ❌ 不得從 `sampleDeck.ts` 動態讀取資料（應從 `public/deck.json` 讀取）
- ❌ 不得在前端直接處理文字分析邏輯（必須透過 Backend API 處理）
- ❌ 不得在 UI 中顯示終端指令讓使用者複製（應直接呼叫 API）
- ❌ 不得使用 WebSocket、Server-Sent Events 等複雜的即時通訊（使用簡單的 HTTP POST 即可）

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

### Backend 參數與整合
- ✅ 提供參數輸入介面（分群閾值、最大主題數、每卡摘要數、除錯模式）
- ✅ 所有參數都有明確的預設值，使用者可選擇性修改
- ✅ 參數範圍驗證正確（閾值 0.0–1.0，主題數 1–10，摘要數 1–5）
- ✅ 「生成卡片」按鈕能將文字和參數透過 HTTP POST 送到 Backend API
- ✅ 顯示載入中狀態，處理完成後自動更新顯示
- ✅ 顯示處理結果訊息（成功或失敗）

### 整合測試
- ✅ 完整流程測試：
  1. 確認 Backend API server 已啟動（`http://127.0.0.1:8000`）
  2. 上傳測試檔案或輸入文字 → 調整參數 → 點擊「生成卡片」
  3. 顯示載入中狀態 → Backend 處理完成
  4. 自動更新顯示 → 新卡片正確顯示
  5. 整個流程順暢，無需手動複製指令或重新載入

### 錯誤處理
- ✅ 各種異常情況都有清楚的使用者提示
- ✅ **確認無 URL 輸入欄位**，不支援網頁抓取功能
- ✅ **確認無終端指令複製區**（直接呼叫 API，不需要使用者手動執行指令）
- ✅ Backend 連接失敗時有明確提示

> 📋 **更多測試案例**：邊界條件、錯誤處理、瀏覽器相容性測試請參閱 `technical-spec.md`

## 風險與緩解
- **JSON 版本差異**：固定 schema，必要時增加向後相容映射
- **大檔渲染**：使用分頁/虛擬列表策略，顯示 loading
- **瀏覽器差異**：優先桌面 Chrome/Edge，明確標示支援範圍
- **API 連接問題**：Backend 未啟動或網路問題，提供清楚的錯誤提示和重試機制
- **CORS 問題**：確保 Backend 正確設定 CORS，允許前端 origin

## 與其他模組的關係
- **資料來源**：從 Agent A 產生的 `public/deck.json` 讀取資料
- **輸入處理**：讀取檔案內容後，透過 HTTP API 呼叫 Agent A 進行處理
- **整合方式**：直接呼叫 Agent A 的 FastAPI endpoint（`POST http://127.0.0.1:8000/api/process`）

> 📋 **整合流程詳見**：`docs/prd/global.md` - "整合任務" 章節
