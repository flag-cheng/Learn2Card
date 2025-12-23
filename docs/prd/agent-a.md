# Agent A PRD：核心 NLP/LLM 管線

## 使命
實作從「文件→段落→重點/關鍵詞→語意分群→卡片草稿→統計」的核心演算法/LLM 流程，輸出穩定 JSON，供其他模組使用。

## 技術棧與環境
> 📋 **請參閱**：技術棧與環境設定的完整規範請參考 `.cursor/rules/backend-rule.mdc`

- **專案位置**：`backend/` 目錄
- **技術棧**：Python 3.11+ + uv 套件管理器
- **輸入來源限制**：本模組僅接受**純文字字串**作為輸入，不處理檔案讀取、URL 抓取或任何 I/O 操作。檔案讀取應由呼叫方（如 Agent B）負責。

## 對外介面（與 Agent B 對接）
> 📋 **詳細技術規範請參閱**：`docs/spec/technical-spec.md` - "Agent A：Backend CLI 介面規範" 章節

### 簡要說明
- **程式位置**：`backend/main.py`
- **執行方式**：`cd backend && uv run python main.py --text "輸入文字"`
- **輸出位置**：固定輸出到 `frontend/public/deck.json`（UTF-8 編碼）
- **輸出格式**：符合 `frontend/src/types.ts` 的 `Deck` 型別
- **回傳值**：成功時 exit code 0，失敗時非 0

完整的 CLI 參數、執行範例、錯誤處理等技術細節，請參閱 technical-spec.md。

## 功能需求

### 核心功能
1. **段落切分**：依標題/空行/清單切分，保留來源索引
2. **重點抽取**：每段一句話摘要 + 1–5 個關鍵詞
3. **向量化與分群**：使用閾值分群（`topicThreshold`，預設 0.75），至少產生 1 個主題
4. **卡片草稿生成**：每主題 1 張卡；若段落數 > 8 則拆成 2 張；每卡 1–5 bullets（目標 3–5）
5. **統計計算**：段落數、主題數、卡片數
6. **JSON 輸出**：寫入 `frontend/public/deck.json`（UTF-8 編碼，無 BOM）

### 參數化
- 分群閾值（`--topic-threshold`，預設 0.75）
- 最大主題數（`--max-topics`，預設 5）
- 每卡摘要數上限（`--max-bullets`，預設 5）
- 除錯模式（`--debug`）

### 可測性
提供 CLI 介面，能顯示中間結果（使用 `--debug` 參數）。

> 📋 **技術細節**：完整的參數說明、處理流程、錯誤處理規範請參閱 `technical-spec.md` - "Agent A：Backend CLI 介面規範" 章節

## 非功能需求
- **效能**：5k tokens 級別可在合理時間內完成
- **錯誤處理**：輸入空檔/過長/編碼錯誤要有明確訊息
- **可替換性**：LLM/embedding/聚類實作可抽換，介面固定
- **編碼**：輸出檔案必須使用 UTF-8 編碼（無 BOM），確保中文等多語言內容正確顯示

## 實作指引與限制
> 📋 **請參閱**：通用 Backend 開發規則請參考 `.cursor/rules/backend-rule.mdc`

### 本模組特定限制

#### 必須遵守
- **輸入介面**：CLI 的 `--text` 參數必須接受**純文字字串**，不接受檔案路徑或 URL
- **檔案讀取**：本模組不負責讀取輸入檔案，檔案讀取由呼叫方處理
- **檔案寫入**：固定輸出到 `frontend/public/deck.json`，使用 UTF-8 編碼（無 BOM）
- **輸出格式**：必須輸出符合 `frontend/src/types.ts` 的 `Deck` 型別，確保 deterministic 排序
- **目錄建立**：若 `frontend/public/` 目錄不存在，應自動建立

#### 不得實作
- ❌ 不得在核心管線中處理**輸入檔案讀取**、URL 抓取或其他輸入 I/O 操作
- ❌ 不得假設輸入來源（讓呼叫方決定如何取得文字）
- ❌ 不得在未經明確需求的情況下新增額外 LLM 提供者或 embedding 模型
- ❌ 不得使用非 UTF-8 編碼輸出檔案（避免中文亂碼）
- ❌ **不得提供 `--output` 或 `-o` 參數**（輸出位置固定為 `frontend/public/deck.json`）
- ❌ **不得支援 stdout 輸出或管道操作**（避免複雜化）
- ❌ **不得提供自訂輸出路徑功能**（避免浪費 token 實作不必要的彈性）

## 驗收標準

> 📋 **詳細驗收標準請參閱**：`technical-spec.md` - "Agent A 驗收（M2）" 章節

### 對外介面驗證（與 Agent B 對接）
- ✅ 程式位置：`backend/main.py` 存在且可執行
- ✅ 指令格式：`cd backend && uv run python main.py --text "..."` 能正常執行
- ✅ 必要參數：`--text` 參數必須存在且為必填
- ✅ 輸出位置：執行後固定產生 `frontend/public/deck.json`
- ✅ Exit code：成功時回傳 0，失敗時回傳非 0
- ✅ 錯誤訊息：失敗時在 stderr 輸出明確的錯誤訊息

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
- ✅ 確認無 `--output` 參數或 `-o` 選項（輸出位置固定）
- ✅ 確認無 stdout JSON 輸出（避免不必要的實作）
- ✅ CLI 不涉及輸入檔案讀取（輸入透過 `--text` 參數傳入純文字字串）

> 📋 **更多細節**：完整的驗收檢查清單、測試用例、邊界條件處理請參閱 `technical-spec.md`

## 風險與緩解
- **LLM 漂移**：提供 deterministic 設定；允許替換模型
- **分群品質**：暴露群數/閾值；輸出中間相似度供調試
- **成本/時延**：控制輸入長度；可分批或降採樣
- **編碼問題**：強制使用 UTF-8 編碼，在 Windows 環境下測試中文處理

## 與其他模組的關係
- **輸入來源**：由 Agent B（Frontend）讀取檔案後傳入
- **輸出目標**：產生的 `deck.json` 由 Agent B（Frontend）載入顯示
- **整合方式**：Agent B 產生執行指令 → 使用者手動執行 → Agent A 更新 `deck.json` → Agent B 重新載入

> 📋 **整合流程詳見**：`docs/prd/global.md` - "整合任務" 章節
