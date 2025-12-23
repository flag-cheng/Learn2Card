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

完成這些準備後，再開始實作檔案上傳和 Agent A 呼叫功能。

## 範圍
- **資料來源輸入（嚴格限制）**：  
  - **僅支援**上傳 `.txt` 或 `.md` 檔案（讀取檔案內容為純文字字串）  
  - **或**提供文字框讓使用者直接貼上純文字內容  
  - **不支援 URL 輸入**、網頁抓取或其他格式檔案（如 PDF、DOCX 等）  
- **卡片資料來源**：
  - 初始載入時，從 `public/deck.json` 讀取預設範例卡片（需先將 `sampleDeck.ts` 資料轉存為 JSON）
  - 使用者上傳檔案或貼上文字後，呼叫 Agent A 處理，Agent A 會更新 `public/deck.json`
  - Frontend 重新載入 `public/deck.json` 以顯示新卡片
- **資料處理流程**：  
  1. 讀取 `.txt` 或 `.md` 檔案內容（或取得文字框內容）
  2. 將純文字字串傳給 Agent A 的核心管線
  3. Agent A 處理後自動產生 `frontend/public/deck.json`
  4. Frontend 重新載入並顯示卡片  
- 卡片呈現：標題 + 1–5 摘要（目標 3–5），上一張/下一張、分頁控制、鍵盤左右鍵。  
- 統計區：段落/主題/卡片數（對應 stats.paragraphCount、stats.topicCount、stats.cardCount）。  
- 主題瀏覽：依 topic 跳轉或篩選。  
- 錯誤提示：資料格式錯誤或載入失敗的提示。

## 資料介面（JSON）
**重要**：必須使用與前端 `frontend/src/types.ts` 完全一致的 `Deck` 型別格式。

- `paragraphs`: [{id: string, text: string, summary: string, keywords: string[], sourceIndex: number}]  
- `topics`: [{id: string, title: string, memberIds: string[]}]  
- `cards`: [{id: string, topicId: string, title: string, bullets: string[]}]  
- `stats`: {paragraphCount: number, topicCount: number, cardCount: number}

### 資料流（方案 A：簡易 Demo 版）
1. **初始狀態**：Frontend 從 `public/deck.json` 讀取預設範例（需先從 `sampleDeck.ts` 轉存）
2. **處理流程**：
   - 使用者上傳檔案或貼上文字
   - Frontend 讀取內容為純文字字串並顯示
   - Frontend 產生可執行的指令（含跳脫字元處理）並提供「複製指令」按鈕
   - **使用者手動**到終端執行該指令：
     ```bash
     cd backend && uv run python main.py --text "..."
     ```
   - Backend 執行完成後自動更新 `frontend/public/deck.json`
   - 使用者點擊「重新載入卡片」按鈕
3. **顯示更新**：Frontend 重新 `fetch('/deck.json')` 並渲染新卡片

此格式由 Agent A 輸出，Agent B 載入後直接使用，確保前後端資料結構完全對齊。

## 功能需求
1) **輸入方式（嚴格限制）**：  
   - 提供檔案上傳按鈕，**僅接受 `.txt` 和 `.md` 格式**  
   - 讀取檔案內容後，取得**純文字字串**（使用 FileReader API）
   - 或提供多行文字輸入框，讓使用者直接貼上純文字內容  
   - **不得**提供 URL 輸入欄位或網頁抓取功能  
   - 顯示載入中狀態與進度提示
1.5) **Backend 處理方式**（兩種實作路徑，擇一）：

   **方案 A：簡易 Demo 版（推薦用於 P0）**
   - 將文字內容儲存到 `public/input.txt` 或顯示在畫面上
   - 提示使用者手動執行 Backend 指令：
     ```bash
     cd backend
     uv run python main.py --text "複製這段文字"
     ```
   - 或提供「複製指令」按鈕，方便使用者貼到終端執行
   - Backend 執行完成後，使用者點擊「重新載入」按鈕，Frontend 重新 `fetch('/deck.json')`
   
   **方案 B：完整整合版（需額外建立 API）**
   - Backend 需提供 HTTP API（如 Flask/FastAPI）監聽 `localhost:8000`
   - API 端點：`POST /api/generate` 接收 `{ "text": "..." }` JSON
   - API 呼叫 `generate_deck()` 函式並寫入 `frontend/public/deck.json`
   - Frontend 使用 `fetch('http://localhost:8000/api/generate', {method: 'POST', ...})` 呼叫
   - **注意**：方案 B 需在 Backend 額外實作 HTTP server（不在目前 Agent A 範圍內）
   
   **本 PRD 採用方案 A**（簡易 Demo 版），避免複雜化。  
2) **指令產生與複製**：
   - 將使用者輸入的文字進行跳脫處理（處理引號、換行、特殊字元）
   - 產生可執行的指令字串：`cd backend && uv run python main.py --text "..."`
   - 提供「複製指令」按鈕，點擊後複製到剪貼簿
   - 顯示執行提示：「請到終端執行上方指令」
3) **重新載入功能**：
   - 提供「重新載入卡片」按鈕
   - 點擊後執行 `fetch('/deck.json')` 重新讀取並渲染
4) 導航：上一張/下一張；分頁（例如每頁 N 張）；鍵盤左右鍵快捷。  
5) 主題跳轉：依 topic 過濾/跳轉，顯示主題標題。  
6) 統計展示：同步顯示段落/主題/卡片數（使用 stats.paragraphCount、stats.topicCount、stats.cardCount）。  
7) 錯誤處理：  
   - 檔案格式驗證：若上傳非 txt/md 檔案，顯示明確錯誤訊息  
   - JSON schema 驗證：載入的 JSON 格式錯誤時提供可讀提示  
   - 空內容處理：文字為空或無效時的友善提示  
8) UI：簡潔、可讀，行高、對比度足夠。

## 非功能需求（品質與效能要求）
> 💡 **說明**：「非功能需求」指的不是具體功能，而是系統的品質、效能、相容性等要求。

- **瀏覽器相容性**：優先支援 Chrome/Edge 桌面版，在 Windows 環境下正常運作。  
- **部署方式**：使用 Vite 的開發伺服器（`npm run dev`），或打包成靜態檔案（`npm run build`）。  
- **回應速度**：大檔案處理時要顯示 loading 狀態，避免長時間白屏或無回應。  
- **錯誤處理**：任何錯誤（檔案格式、JSON 解析、API 呼叫失敗等）都要有清楚的使用者提示。  
- **程式碼品質**：使用 TypeScript 型別檢查，確保型別安全。

## 實作指引與限制
> 📋 **請參閱**：通用 Frontend 開發規則請參考 `.cursor/rules/frontend-rule.mdc`

### 本模組特定限制
#### 必須遵守
- **輸入格式**：只接受 `.txt` 和 `.md` 檔案上傳，或純文字貼上  
- **檔案驗證**：上傳時檢查副檔名，非 txt/md 要明確拒絕並顯示錯誤訊息  
- **檔案讀取**：使用 FileReader API 讀取 `.txt` 或 `.md` 檔案內容為純文字字串
- **Backend 整合方式**（採用方案 A：簡易 Demo 版）：
  - 將使用者輸入的文字顯示在畫面上或儲存到 `public/input.txt`
  - 提供「複製指令」按鈕，產生可執行的指令：
    ```bash
    cd backend && uv run python main.py --text "使用者的文字"
    ```
  - 提示使用者到終端執行該指令
  - 提供「重新載入卡片」按鈕，執行 `fetch('/deck.json')` 重新載入資料
  - **不需要**在 Frontend 中執行系統指令（瀏覽器無法做到）
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
- ❌ **不得實作 HTTP API server**（除非明確要求方案 B，目前採用方案 A）
- ❌ 不得使用 WebSocket、Server-Sent Events 等複雜的即時通訊（保持簡單）  

## 驗收標準
- **專案完整性**：`frontend/` 目錄結構維持不變，`npm install` 和 `npm run dev` 能正常執行。  
- **初始資料**：`public/deck.json` 已存在（從 `sampleDeck.ts` 轉存），頁面載入時顯示預設範例卡片。
- **資料來源**：Frontend 從 `public/deck.json` 載入資料，**不從** `sampleDeck.ts` 讀取。
- **現有功能保留**：原有的卡片瀏覽、主題切換、統計顯示功能繼續運作正常。  
- **檔案讀取功能**：能上傳 .txt 或 .md 檔案，成功讀取檔案內容為純文字字串並顯示。
- **指令產生功能**：能產生正確的 Backend 執行指令（含文字跳脫處理），並提供「複製指令」按鈕。
- **重新載入功能**：提供「重新載入卡片」按鈕，點擊後重新 `fetch('/deck.json')` 並顯示新卡片。
- **整合測試**：
  1. 上傳測試檔案 → 複製指令 → 手動執行 Backend → 點擊重新載入 → 顯示新卡片
  2. 整個流程能順利完成，新卡片正確顯示
- **資料格式驗證**：載入的 JSON 必須符合前端 `Deck` 型別（與 `frontend/src/types.ts` 格式一致）。  
- 能正常翻卡、分頁、群組跳轉。  
- 統計數據與 JSON 一致（使用 paragraphCount、topicCount、cardCount）；錯誤 JSON 能顯示提示。  
- 上傳非 txt/md 檔案時，顯示明確的格式錯誤提示。  
- **確認無 URL 輸入欄位**，不支援網頁抓取功能。  
- 主要操作可被示範（滑鼠/鍵盤）。

## 風險與緩解
- JSON 版本差異：固定 schema，必要時增加向後相容映射。  
- 大檔渲染：使用分頁/虛擬列表策略，顯示 loading。  
- 瀏覽器差異：優先桌面 Chrome/Edge。

