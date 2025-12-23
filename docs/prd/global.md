# 全局 PRD：文件歸納切卡機（雙 Agent 平行示範）

## 本 PRD 的角色
**本 PRD（global.md）負責整合 Agent A 和 Agent B 的實作結果**，具體任務包括：
1. **分支整合**：將 Agent A 和 Agent B 各自由 Cloud Agent 自動產生的開發分支 merge，產生新的整合分支（不直接動到 master）
2. **流程驗證**：在整合分支上確保完整的「上傳 → 後端分析 → 即時出卡」流程正常運作
3. **端對端測試**：驗證前後端整合無誤，使用者可以上傳文件並看到生成的卡片
4. **分支資訊**：Agent A 和 Agent B 的分支名稱由 Cloud Agent 自動產生，將在實作完成後提供

## 專案目標
- **目的**：示範 Cursor（地端）+ Cloud Agent（遠端 GitHub）協作；本機有 UI，可啟動並瀏覽卡片。
- **輸入**：Markdown/純文字（`.md` 或 `.txt` 檔案），暫不支援 PDF。
- **處理流程**：
  1. 切段（依標題、空行、清單）
  2. 每段一句摘要 + 關鍵詞
  3. Embedding 向量化與相似度分群
  4. 產生卡片（每卡標題 + 1–5 bullets，目標 3–5）
  5. 統計段落/主題/卡片數
  6. 輸出 `frontend/public/deck.json`（UTF-8 編碼）
- **整合方式**（簡易 Demo 版）：
  - Frontend 上傳檔案 → 產生指令
  - 使用者手動到終端執行 Backend 指令
  - Backend 更新 `deck.json` → Frontend 重新載入並顯示
  - **不使用 HTTP API**，保持簡單
- **並行開發**：Agent A（Backend）與 Agent B（Frontend）可同時開發，透過固定的 `deck.json` 介面對接。

## 既有資產（P0）
- **Frontend 基礎**：React + TypeScript + Vite 專案（`frontend/` 目錄），已有基本卡片瀏覽介面（`src/App.tsx`）。
- **範例資料**：`frontend/src/sampleDeck.ts` 包含範例卡片資料（需轉存為 `public/deck.json`）。
- **型別定義**：`frontend/src/types.ts` 定義 `Deck` 型別（Backend 輸出必須符合此格式）。
- **Backend 基礎**：Python 專案結構（`backend/` 目錄），已有 `pyproject.toml` 和基本程式碼。
- **規格文件**：PRD（`docs/prd/`），包含 `global.md`、`agent-a.md`、`agent-b.md`。
- **開發規則**：`.cursor/rules/` 包含 backend 和 frontend 開發規則。
- **無需自動化 GitHub**（C-agent）；演示以截圖/文章呈現。

## 範圍內
- 固定的 deck JSON schema（paragraphs/topics/cards/stats 等核心欄位、卡片 bullets 規格）；輸出固定放 `frontend/public/deck.json`，UI 以 `fetch('/deck.json')` 讀取。
- **A-agent（後端）**：
  - CLI 程式位置：`backend/main.py`
  - 執行方式：`cd backend && uv run python main.py --text "..."`
  - 固定輸出到 `frontend/public/deck.json`（UTF-8 編碼）
  - **不提供 HTTP API**（採用簡易 Demo 版，避免複雜化）
- **B-agent（前端）**：
  - 從 `public/deck.json` 載入卡片資料（初始需將 `sampleDeck.ts` 轉存）
  - 支援上傳 `.txt` 或 `.md` 檔案，讀取內容為純文字
  - 產生可執行的後端指令並提供「複製指令」按鈕
  - 提供「重新載入卡片」按鈕，重新 `fetch('/deck.json')`
  - 支援翻卡、分頁、統計、主題跳轉、錯誤提示
- **整合任務（本 PRD）**：
  - Merge Agent A 和 Agent B 的開發分支，產生新的整合分支
  - 確保「上傳檔案 → 產生指令 → 手動執行 Backend → 重新載入」的完整流程運作
  - 驗證 Backend 輸出的 `deck.json` 能被 Frontend 正確讀取和顯示
  - 處理可能的整合問題（路徑、編碼、JSON schema 一致性等）
  - 驗證通過後再考慮 merge 到 master

## 範圍外
- 帳號/權限/多人協作功能；PDF 解析；精緻動畫；成本最佳化策略。

## 成功指標（MVP）
- **Frontend 正常運作**：本地啟動 Frontend，從 `public/deck.json` 載入資料，正常翻卡、分頁、統計、主題跳轉、錯誤提示。
- **Backend 正常運作**：執行 `cd backend && uv run python main.py --text "..."` 能成功產生 `frontend/public/deck.json`，格式正確、編碼無誤。
- **檔案上傳功能**：Frontend 能上傳 `.txt` 或 `.md` 檔案，讀取內容並產生可執行的 Backend 指令。
- **完整流程打通**：上傳檔案 → 複製指令 → 執行 Backend → 重新載入 → 顯示新卡片，整個流程順暢。
- **JSON schema 穩定**：Backend 輸出格式與 Frontend 的 `types.ts` 完全一致，兩 Agent 可並行開發並正確對接。

## 里程碑
- **M1（P0）**：專案基礎架構、範例資料、型別定義、規格文件齊備。✅
- **M2（Agent A）**：Backend 實作完成（由 Cloud Agent 在獨立分支實作）
  - 程式位置：`backend/main.py`
  - 執行方式：`cd backend && uv run python main.py --text "..."`
  - 固定輸出到 `frontend/public/deck.json`
- **M3（Agent B）**：Frontend 實作完成（由 Cloud Agent 在獨立分支實作）
  - 從 `public/deck.json` 載入並顯示卡片
  - 檔案上傳、指令產生、重新載入功能
  - 卡片瀏覽、統計、主題跳轉功能
- **M4（整合）**：Merge A/B 分支到新的整合分支，完整流程驗證。（本 PRD 負責此階段）
  - 端對端測試：上傳 → 執行 → 重新載入 → 顯示
  - 驗證 JSON schema 一致性、編碼正確性、路徑正確性
- **M5（發布）**：整合分支驗收通過後，merge 到 master。（視情況執行）

## 風險與緩解
- **Schema 變動風險**：鎖定 schema，任何變更需明示版本與遷移。
- **資料品質**：LLM 漂移與分群品質，用 deterministic 設定、暴露群數/閾值；提供 validate 檢查必填欄位/ bullets 數量。
- **平台差異**：Windows CRLF/編碼，規定 UTF-8 輸出；行尾一致。
- **整合風險**：
  - 分支衝突：Agent A 和 Agent B 可能修改相同檔案，在整合分支上需仔細 review 並解決 merge conflicts
  - 路徑問題：Backend 輸出到 `../frontend/public/deck.json`，Frontend 從 `public/deck.json` 讀取，需確認相對路徑正確
  - JSON schema 一致性：Backend 輸出格式必須與 Frontend 的 `types.ts` 完全一致
  - 編碼問題：Backend 輸出 UTF-8（無 BOM），Frontend 讀取時需正確解析，避免中文亂碼
  - 初始資料準備：需將 `sampleDeck.ts` 轉存為 `public/deck.json` 作為初始範例資料
  - 環境差異：確保前後端都能在 Windows 本地環境正常啟動（在整合分支上測試）
  - 指令跳脫處理：Frontend 產生的指令需正確處理特殊字元（引號、換行等）
  - 整合分支隔離：在整合分支上完成所有測試後，再 merge 到 master，避免破壞 master 的穩定性

## 驗收標準

### Agent A 驗收（M2）
- **程式位置**：`backend/main.py` 存在且可執行
- **執行測試**：`cd backend && uv run python main.py --text "範例文字..."` 執行成功
- **輸出驗證**：
  - 自動產生 `frontend/public/deck.json`
  - JSON 格式符合 `frontend/src/types.ts` 的 `Deck` 型別
  - 包含完整欄位：paragraphs、topics、cards、stats
  - UTF-8 編碼，中文無亂碼
- **Exit code**：成功時回傳 0，失敗時回傳非 0
- **統計正確**：stats 中的 paragraphCount、topicCount、cardCount 數值正確

### Agent B 驗收（M3）
- **初始載入**：`frontend/public/deck.json` 存在，啟動時能正常顯示卡片
- **卡片瀏覽**：翻卡、分頁/序列、統計、主題跳轉、錯誤提示均正常
- **檔案上傳**：能上傳 `.txt` 或 `.md` 檔案，讀取內容為純文字字串
- **文字輸入**：能在文字框貼上純文字內容
- **指令產生**：能產生正確的 Backend 執行指令（含跳脫字元處理）
- **複製功能**：「複製指令」按鈕能將指令複製到剪貼簿
- **重新載入**：「重新載入卡片」按鈕能重新 `fetch('/deck.json')` 並更新顯示
- **錯誤處理**：上傳非 `.txt`/`.md` 檔案時顯示清楚錯誤訊息

### 整合驗收（M4 - 本 PRD 負責）
- **分支整合成功**：Agent A 和 Agent B 的分支已 merge 到新的整合分支，無衝突或衝突已解決。
- **初始資料準備**：`frontend/public/deck.json` 已存在（從 `sampleDeck.ts` 轉存），Frontend 啟動時能正常載入並顯示範例卡片。
- **Backend 獨立驗證**（在整合分支上執行）：
  1. 執行 `cd backend && uv run python main.py --text "測試文字..."`
  2. 確認 `frontend/public/deck.json` 成功產生並更新
  3. 確認 JSON 格式符合 `frontend/src/types.ts` 的 `Deck` 型別
  4. 確認 UTF-8 編碼正確，中文無亂碼
- **Frontend 獨立驗證**（在整合分支上執行）：
  1. Frontend 啟動後從 `public/deck.json` 載入資料
  2. 能正常翻卡、切換主題、查看統計
  3. 上傳 `.txt` 或 `.md` 檔案後，能讀取內容並顯示
  4. 能產生正確的 Backend 執行指令（含跳脫字元處理）
  5. 「複製指令」和「重新載入卡片」按鈕功能正常
- **端對端整合測試**（完整流程）：
  1. Frontend 啟動，顯示初始範例卡片
  2. 上傳真實的 `.md` 檔案（或貼上文字）
  3. 複製 Frontend 產生的指令
  4. 到終端手動執行該指令：`cd backend && uv run python main.py --text "..."`
  5. 確認 Backend 執行成功（exit code 0）並更新 `deck.json`
  6. 回到 Frontend 點擊「重新載入卡片」
  7. 確認新卡片正確顯示，可以翻卡、查看統計
- **錯誤處理驗證**：
  - 上傳非 `.txt`/`.md` 檔案，顯示清楚錯誤提示
  - Backend 執行失敗時（exit code 非 0），錯誤訊息清楚
  - JSON 格式錯誤時，Frontend 能捕捉並提示
- **準備 merge 到 master**：所有驗收通過後，整合分支可以安全地 merge 到 master。

