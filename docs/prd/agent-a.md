# Agent A PRD：核心 NLP/LLM 管線（Backend 專責）

## 職責範圍
**Agent A 僅負責 Backend（後端處理）**：
- ✅ 提供 HTTP API 接收純文字輸入和處理參數
- ✅ 執行文本分析與卡片生成邏輯
- ✅ 輸出 JSON 到固定位置（`frontend/public/deck.json`）
- ✅ 回傳處理結果給前端
- ❌ **不負責** Frontend UI
- ❌ **不負責** 檔案讀取（由 Agent B 處理）
- ❌ **不負責** 使用者互動（由 Agent B 處理）

## 使命
實作從「文件→段落→重點/關鍵詞→語意分群→卡片草稿→統計」的核心演算法/LLM 流程，輸出穩定 JSON，供 Agent B（Frontend）使用。

## 技術棧與環境
> 📋 **請參閱**：技術棧與環境設定的完整規範請參考 `.cursor/rules/backend-rule.mdc`

- **專案位置**：`backend/` 目錄
- **技術棧**：Python 3.11+ + FastAPI + uvicorn + uv 套件管理器
- **輸入來源限制**：本模組僅接受**純文字字串**作為輸入，不處理檔案讀取、URL 抓取或任何 I/O 操作。檔案讀取應由呼叫方（如 Agent B）負責。

## 對外介面（與 Agent B 對接）
> 📋 **詳細技術規範請參閱**：`docs/spec/technical-spec.md` - "Agent A：Backend API 介面規範" 章節

### 簡要說明
- **實作方式**：FastAPI HTTP API server
- **主程式位置**：`backend/api.py`（或 `main.py` 包含 FastAPI 路由）
- **執行方式**：`cd backend && uv run uvicorn api:app --reload --host 127.0.0.1 --port 8000`
- **API Endpoint**：`POST http://127.0.0.1:8000/api/process`
- **Request Body**：JSON 格式，包含 `text`（必填）及可選參數（`topic_threshold`, `max_topics`, `max_bullets`, `debug`）
- **Response**：JSON 格式，包含處理結果、統計資訊、完整 deck 資料
- **副作用**：固定輸出到 `frontend/public/deck.json`（UTF-8 編碼）
- **CORS 設定**：允許前端（`http://localhost:5173`）呼叫 API

完整的 API 規格、Request/Response Schema、錯誤處理等技術細節，請參閱 technical-spec.md。

## 功能需求

### 核心功能
1. **段落切分**：依標題/空行/清單切分，保留來源索引
2. **重點抽取**：每段一句話摘要 + 1–5 個關鍵詞
3. **向量化與分群**：使用閾值分群（`topicThreshold`，預設 0.75），至少產生 1 個主題
4. **卡片草稿生成**：每主題 1 張卡；若段落數 > 8 則拆成 2 張；每卡 1–5 bullets（目標 3–5）
5. **統計計算**：段落數、主題數、卡片數
6. **JSON 輸出**：寫入 `frontend/public/deck.json`（UTF-8 編碼，無 BOM）

### 參數化
- 分群閾值（`topic_threshold`，預設 0.75）
- 最大主題數（`max_topics`，預設 5）
- 每卡摘要數上限（`max_bullets`，預設 5）
- 除錯模式（`debug`，預設 false）

### 可測性
提供 HTTP API 介面，支援除錯模式（`debug: true`）輸出中間結果。

> 📋 **技術細節**：完整的參數說明、處理流程、錯誤處理規範請參閱 `technical-spec.md` - "Agent A：Backend API 介面規範" 章節

## 非功能需求
- **效能**：5k tokens 級別可在合理時間內完成
- **錯誤處理**：輸入空檔/過長/編碼錯誤要有明確訊息
- **可替換性**：LLM/embedding/聚類實作可抽換，介面固定
- **編碼**：輸出檔案必須使用 UTF-8 編碼（無 BOM），確保中文等多語言內容正確顯示

## 實作指引與限制
> 📋 **請參閱**：通用 Backend 開發規則請參考 `.cursor/rules/backend-rule.mdc`

### 本模組特定限制

#### 必須遵守
- **輸入介面**：API 的 `text` 欄位必須接受**純文字字串**，不接受檔案路徑或 URL
- **檔案讀取**：本模組不負責讀取輸入檔案，檔案讀取由呼叫方（Agent B）處理
- **檔案寫入**：固定輸出到 `frontend/public/deck.json`，使用 UTF-8 編碼（無 BOM）
- **輸出格式**：必須輸出符合 `frontend/src/types.ts` 的 `Deck` 型別，確保 deterministic 排序
- **目錄建立**：若 `frontend/public/` 目錄不存在，應自動建立
- **CORS 設定**：必須設定 CORS 允許前端 origin（`http://localhost:5173`, `http://127.0.0.1:5173`）
- **API 規格**：使用 Pydantic models 定義 Request/Response schema，提供明確的欄位驗證

#### 不得實作
- ❌ 不得在核心管線中處理**輸入檔案讀取**、URL 抓取或其他輸入 I/O 操作
- ❌ 不得假設輸入來源（讓呼叫方決定如何取得文字）
- ❌ 不得在未經明確需求的情況下新增額外 LLM 提供者或 embedding 模型
- ❌ 不得使用非 UTF-8 編碼輸出檔案（避免中文亂碼）
- ❌ **不得提供自訂輸出路徑參數**（輸出位置固定為 `frontend/public/deck.json`）
- ❌ **不得實作檔案上傳 endpoint**（檔案讀取由前端處理，只接收純文字）
- ❌ **不得實作認證或授權機制**（僅限本地開發使用，避免複雜化）

## 驗收標準

> 📋 **詳細驗收標準請參閱**：`technical-spec.md` - "Agent A 驗收（M2）" 章節

### 對外介面驗證（與 Agent B 對接）
- ✅ API server 能正常啟動：`cd backend && uv run uvicorn api:app --reload`
- ✅ API endpoint 存在：`POST http://127.0.0.1:8000/api/process`
- ✅ Request 格式正確：接收 JSON body 包含 `text` 欄位（必填）和可選參數
- ✅ 必要參數驗證：`text` 欄位為空時回傳 400 錯誤
- ✅ 輸出位置：處理成功後固定產生 `frontend/public/deck.json`
- ✅ HTTP status code：成功時 200，參數錯誤 400，內部錯誤 500
- ✅ 錯誤訊息：失敗時在 Response body 回傳明確的錯誤訊息
- ✅ CORS 設定：前端能成功呼叫 API（無跨域錯誤）

### 輸出品質
- ✅ JSON 格式符合 `frontend/src/types.ts` 的 `Deck` 型別
- ✅ 包含完整欄位：paragraphs、topics、cards、stats
- ✅ UTF-8 編碼，中文無亂碼
- ✅ 統計數值正確（stats 與實際數量一致）
- ✅ 排序一致（同一輸入重跑，topic/card 順序相同）

### 內容品質
- ✅ 切段、重點抽取主觀滿意度 ≥ 80%
- ✅ 分群結果可讀，卡片 bullets 1–5 條（目標 3–5）

### 限制確認
- ✅ 確認無自訂輸出路徑參數（輸出位置固定）
- ✅ 確認無檔案上傳 endpoint（只接收純文字字串）
- ✅ 確認無認證機制（本地開發用，保持簡單）
- ✅ API 不涉及輸入檔案讀取（輸入透過 request body 的 `text` 欄位傳入純文字字串）

> 📋 **更多細節**：完整的驗收檢查清單、測試用例、邊界條件處理請參閱 `technical-spec.md`

## 風險與緩解
- **LLM 漂移**：提供 deterministic 設定；允許替換模型
- **分群品質**：暴露群數/閾值；輸出中間相似度供調試
- **成本/時延**：控制輸入長度；可分批或降採樣
- **編碼問題**：強制使用 UTF-8 編碼，在 Windows 環境下測試中文處理

## 與其他模組的關係
- **輸入來源**：由 Agent B（Frontend）讀取檔案後透過 HTTP API 傳入
- **輸出目標**：產生的 `deck.json` 由 Agent B（Frontend）重新載入顯示
- **整合方式**：Agent B 呼叫 API → Agent A 處理並更新 `deck.json` → 回傳結果 → Agent B 重新載入並顯示

> 📋 **整合流程詳見**：`docs/prd/global.md` - "整合任務" 章節
