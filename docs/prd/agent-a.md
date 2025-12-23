# Agent A PRD：核心 NLP/LLM 管線

## 使命
實作從「文件→段落→重點/關鍵詞→語意分群→卡片草稿→統計」的核心演算法/LLM 流程，輸出穩定 JSON，供其他模組使用。

## 技術棧與環境
> 📋 **請參閱**：技術棧與環境設定的完整規範請參考 `.cursor/rules/backend-rule.mdc`

- **專案位置**：`backend/` 目錄
- **技術棧**：Python 3.11+ + uv 套件管理器
- **輸入來源限制**：本模組僅接受**純文字字串**作為輸入，不處理檔案讀取、URL 抓取或任何 I/O 操作。檔案讀取應由呼叫方（如 Agent B 或其他模組）負責。

## 範圍
- 段落切分（Markdown/純文字），保留來源索引與標題階層；規則寫死，先不做聰明合併。  
- 重點一句 + 關鍵詞抽取（LLM/embedding 可替換）。  
- 向量化與語意分群：僅用閾值分群（`topicThreshold`，預設 0.75），並可設定 `maxTopics`（預設 5，且至少 1 個主題）。  
- 卡片草稿生成：每主題預設 1 張卡；若 `memberIds.length > 8`，可拆成 2 張卡；每張卡標題 + 1–5 摘要（目標 3–5）。  
- 統計：段落數、主題數、卡片數（對應 stats.paragraphCount、stats.topicCount、stats.cardCount）。  
- 日誌/除錯：可選擇輸出中間結果。

## 對外介面規範（重要：與 Agent B 對接）

### CLI 程式位置與執行方式
- **程式位置**：`backend/main.py`（相對於專案根目錄）
- **執行指令**：
  ```bash
  cd backend
  uv run python main.py --text "輸入的純文字內容"
  ```
- **完整指令格式**（從專案根目錄執行）：
  ```bash
  cd backend && uv run python main.py --text "輸入的純文字內容"
  ```

### 必要參數
- `--text`：輸入的純文字字串（**必填**）
  - 類型：string
  - 說明：純文字內容，不接受檔案路徑或 URL
  - 範例：`--text "專案目標是把長文轉成卡片..."`

### 可選參數
- `--topic-threshold`：分群閾值（預設 0.75，範圍 0.0–1.0）
- `--max-topics`：最大主題數（預設 5，最小 1）
- `--max-bullets`：每卡摘要數上限（預設 5，範圍 1–5）
- `--debug`：顯示除錯訊息（加上此參數後在 stderr 顯示統計資訊）

### 輸入
- **原始文字**：透過 `--text` 參數傳入的純文字字串
- **編碼要求**：UTF-8

### 輸出檔案位置（固定）
- **檔案路徑**：`frontend/public/deck.json`（相對於專案根目錄）
- **相對於 backend 目錄**：`../frontend/public/deck.json`
- **編碼**：UTF-8（無 BOM）
- **格式**：JSON（縮排 2 空格，便於閱讀）

### 輸出 JSON Schema
Output JSON（**必須完全符合前端 `frontend/src/types.ts` 的 Deck 型別**，穩定 schema，排序 deterministic）：  
- `paragraphs`: [{id: string, text: string, summary: string, keywords: string[], sourceIndex: number}]  
- `topics`: [{id: string, title: string, memberIds: string[]}]  
- `cards`: [{id: string, topicId: string, title: string, bullets: string[]}]  // bullets 目標 3–5 條  
- `stats`: {paragraphCount: number, topicCount: number, cardCount: number}

**重要**：輸出格式必須與 `frontend/src/types.ts` 完全一致，確保產出的 `deck.json` 可直接供 Frontend 載入。

### 執行結果回饋
- **成功時**：
  - Exit code：0
  - stderr 輸出：
    ```
    ✓ 已成功輸出到：<絕對路徑>/frontend/public/deck.json
      - 段落數：N
      - 主題數：N
      - 卡片數：N
    ```
  - stdout：無輸出（或空）
  
- **失敗時**：
  - Exit code：非 0
  - stderr 輸出：明確的錯誤訊息
  - 常見錯誤：
    - 輸入為空
    - 輸入過長（超過 maxInputChars）
    - 編碼錯誤

### 輸出行為
- **自動建立目錄**：若 `frontend/public/` 目錄不存在，應**自動建立**
- **覆寫模式**：每次執行都會覆寫 `deck.json`（不累加、不備份）

### 執行範例

```bash
# 範例 1：基本用法
cd backend
uv run python main.py --text "專案目標是把長文轉成卡片，方便快速掌握重點。"

# 範例 2：從專案根目錄執行（Agent B 會使用此格式）
cd backend && uv run python main.py --text "專案目標是把長文轉成卡片，方便快速掌握重點。"

# 範例 3：調整參數
cd backend
uv run python main.py --text "你的文字..." --max-topics 3 --topic-threshold 0.8 --debug

# 執行後自動產生：frontend/public/deck.json
```

### 與 Frontend 的整合
- Backend 執行時**固定**產生 `frontend/public/deck.json`
- 該檔案格式必須與 `frontend/src/types.ts` 的 `Deck` 型別完全一致
- **必須**使用 UTF-8 編碼（無 BOM），確保中文等多語言內容正確顯示
- Frontend 透過 `fetch('/deck.json')` 直接讀取此檔案
- **呼叫方式**：Agent B（Frontend）產生指令字串後，由使用者手動到終端執行

## 功能需求
1) 段落切分：依標題/空行/清單，避免過短段落合併；每段需有 id、text、sourceIndex 欄位。  
2) 重點抽取：每段一句話摘要（存入 summary 欄位）+ 關鍵詞（1–5 個，存入 keywords 陣列），可選 deterministic 模式。  
3) 向量化：可配置模型；暴露維度/批次大小；失敗要回傳可讀錯誤。  
4) 分群：僅用相似度閾值 `topicThreshold`，並尊重 `maxTopics` 上限；至少產生 1 個主題；輸出 memberIds 與代表標題。  
5) 卡片草稿：每主題預設 1 張卡；若 `memberIds.length > 8`，可拆成 2 張卡；每卡 bullets 1–5（目標 3–5）。  
6) 統計：計算段落/主題/卡片數（paragraphCount、topicCount、cardCount）；隨輸出一起返回。  
7) 參數化：溫度、top_p、主題上限/閾值、每卡最大摘要數、max tokens。  
8) 可測性：提供 demo CLI 或函式，能打印中間結果。
9) **檔案輸出**：執行後**固定**將 JSON 寫入 `../frontend/public/deck.json`（UTF-8 編碼），自動建立目錄。

## 非功能
- 效能：5k tokens 級別可在合理時間內完成。  
- 錯誤處理：輸入空檔/過長/編碼錯誤要有明確訊息。  
- 可替換：LLM/embedding/聚類實作可抽換，介面固定。

## 實作指引與限制
> 📋 **請參閱**：通用 Backend 開發規則請參考 `.cursor/rules/backend-rule.mdc`

### 本模組特定限制
#### 必須遵守
- **輸入介面**：函式或 CLI 的輸入參數必須是**文字字串**（str），不接受檔案路徑或 URL  
- **檔案讀取**：本模組不負責讀取輸入檔案，檔案讀取由呼叫方處理  
- **檔案寫入**：CLI 可提供選項將結果寫入檔案，必須使用 **UTF-8 編碼（無 BOM）**
- **輸出格式**：必須輸出符合指定 schema 的 JSON，確保 deterministic 排序
- **目錄建立**：寫入檔案時，若目錄不存在應自動建立（使用 `Path.mkdir(parents=True, exist_ok=True)`）

#### 不得實作
- ❌ 不得在核心管線中處理**輸入檔案讀取**、URL 抓取或其他輸入 I/O 操作  
- ❌ 不得假設輸入來源（讓呼叫方決定如何取得文字）  
- ❌ 不得在未經明確需求的情況下新增額外 LLM 提供者或 embedding 模型
- ❌ 不得使用非 UTF-8 編碼輸出檔案（避免中文亂碼）
- ❌ **不得提供 `--output` 或 `-o` 參數**（輸出位置固定為 `../frontend/public/deck.json`）
- ❌ **不得支援 stdout 輸出或管道操作**（避免複雜化，專注於產生 deck.json）
- ❌ **不得提供自訂輸出路徑功能**（避免浪費 token 實作不必要的彈性）

## 驗收標準

### 對外介面驗證（與 Agent B 對接）
- **程式位置**：`backend/main.py` 存在且可執行
- **指令格式**：`cd backend && uv run python main.py --text "..."` 能正常執行
- **必要參數**：`--text` 參數必須存在且為必填
- **輸出位置**：執行後**固定**產生 `frontend/public/deck.json`，不提供其他輸出選項
- **Exit code**：成功時回傳 0，失敗時回傳非 0
- **錯誤訊息**：失敗時在 stderr 輸出明確的錯誤訊息

### 環境與執行
- **環境設定**：必須提供 `pyproject.toml`，並在 README 中說明使用 `uv sync` 安裝依賴、`uv run` 執行程式
- **安裝與執行**：執行 `uv sync` 安裝依賴後，能使用 `uv run python main.py --text "..."` 正常運行

### 輸出品質
- **輸出格式**：給定範例文字字串，輸出 JSON 必須完全符合前端 `Deck` 型別（與 `frontend/src/types.ts` 格式一致）
- **欄位完整性**：paragraphs 包含 id/text/summary/keywords/sourceIndex；topics 包含 id/title/memberIds；cards 包含 id/topicId/title/bullets；stats 包含 paragraphCount/topicCount/cardCount
- **編碼正確性**：輸出檔案必須是 UTF-8 編碼（無 BOM），中文等多語言內容能正確顯示，無亂碼
- **目錄建立**：若 `frontend/public/` 目錄不存在，自動建立
- **執行回饋**：成功後在 stderr 顯示檔案路徑與統計資訊（段落數、主題數、卡片數）

### 內容品質
- 切段、重點抽取主觀滿意度 ≥ 80%
- 分群結果可讀，卡片 bullets 1–5 條（目標 3–5）
- 同一輸入重跑排序一致（topic 依最小段落 sourceIndex 由小到大；card 依 topic 順序；stats 一致）

### 限制確認
- **確認無 `--output` 參數或 `-o` 選項**（輸出位置固定）
- **確認無 stdout JSON 輸出**（避免不必要的實作）
- CLI 不涉及輸入檔案讀取（輸入透過 `--text` 參數傳入純文字字串）

## 風險與緩解
- LLM 漂移：提供 deterministic 設定；允許替換模型。  
- 分群品質：暴露群數/閾值；輸出中間相似度供調試。  
- 成本/時延：控制輸入長度；可分批或降採樣。

