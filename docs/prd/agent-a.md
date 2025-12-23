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

## 輸入/輸出
- Input：原始文字、選項（語言/最大主題數或閾值、每卡摘要數、溫度/seed 等）。  
- Output JSON（**必須完全符合前端 `sampleDeck.ts` 的 Deck 型別**，穩定 schema，排序 deterministic）：  
  - `paragraphs`: [{id: string, text: string, summary: string, keywords: string[], sourceIndex: number}]  
  - `topics`: [{id: string, title: string, memberIds: string[]}]  
  - `cards`: [{id: string, topicId: string, title: string, bullets: string[]}]  // bullets 目標 3–5 條  
  - `stats`: {paragraphCount: number, topicCount: number, cardCount: number}

**重要**：輸出格式必須與 `frontend/src/sampleDeck.ts` 完全一致，確保產出的 `deck.json` 可直接套用到前端。

## 功能需求
1) 段落切分：依標題/空行/清單，避免過短段落合併；每段需有 id、text、sourceIndex 欄位。  
2) 重點抽取：每段一句話摘要（存入 summary 欄位）+ 關鍵詞（1–5 個，存入 keywords 陣列），可選 deterministic 模式。  
3) 向量化：可配置模型；暴露維度/批次大小；失敗要回傳可讀錯誤。  
4) 分群：僅用相似度閾值 `topicThreshold`，並尊重 `maxTopics` 上限；至少產生 1 個主題；輸出 memberIds 與代表標題。  
5) 卡片草稿：每主題預設 1 張卡；若 `memberIds.length > 8`，可拆成 2 張卡；每卡 bullets 1–5（目標 3–5）。  
6) 統計：計算段落/主題/卡片數（paragraphCount、topicCount、cardCount）；隨輸出一起返回。  
7) 參數化：溫度、top_p、主題上限/閾值、每卡最大摘要數、max tokens。  
8) 可測性：提供 demo CLI 或函式，能打印中間結果。

## 非功能
- 效能：5k tokens 級別可在合理時間內完成。  
- 錯誤處理：輸入空檔/過長/編碼錯誤要有明確訊息。  
- 可替換：LLM/embedding/聚類實作可抽換，介面固定。

## 實作指引與限制
> 📋 **請參閱**：通用 Backend 開發規則請參考 `.cursor/rules/backend-rule.mdc`

### 本模組特定限制
#### 必須遵守
- **輸入介面**：函式或 CLI 的輸入參數必須是**文字字串**（str），不接受檔案路徑或 URL  
- **檔案 I/O**：本模組不負責讀取檔案，檔案讀取由呼叫方處理  
- **輸出格式**：必須輸出符合指定 schema 的 JSON，確保 deterministic 排序

#### 不得實作
- ❌ 不得在核心管線中處理檔案讀取、URL 抓取或其他 I/O 操作  
- ❌ 不得假設輸入來源（讓呼叫方決定如何取得文字）  
- ❌ 不得在未經明確需求的情況下新增額外 LLM 提供者或 embedding 模型

## 驗收標準
- **環境設定**：必須提供 `pyproject.toml`，並在 README 中說明使用 `uv sync` 安裝依賴、`uv run` 執行程式。  
- **安裝與執行**：執行 `uv sync` 安裝依賴後，能使用 `uv run python script.py` 正常運行。  
- **輸出格式**：給定範例文字字串，輸出 JSON 必須完全符合前端 `Deck` 型別（與 `frontend/src/sampleDeck.ts` 格式一致），可直接作為前端的 `deck.json` 使用。  
- **欄位完整性**：paragraphs 包含 id/text/summary/keywords/sourceIndex；topics 包含 id/title/memberIds；cards 包含 id/topicId/title/bullets；stats 包含 paragraphCount/topicCount/cardCount。  
- 切段、重點抽取主觀滿意度 ≥ 80%。  
- 分群結果可讀，卡片 bullets 1–5 條（目標 3–5）；同一輸入重跑排序一致（topic 依最小段落 sourceIndex 由小到大；card 依 topic 順序；stats 一致）。  
- CLI 或單元測試可跑通，且不涉及檔案讀取（輸入為文字字串）。

## 風險與緩解
- LLM 漂移：提供 deterministic 設定；允許替換模型。  
- 分群品質：暴露群數/閾值；輸出中間相似度供調試。  
- 成本/時延：控制輸入長度；可分批或降採樣。

