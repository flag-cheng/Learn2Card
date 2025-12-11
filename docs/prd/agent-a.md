# Agent A PRD：核心 NLP/LLM 管線

## 使命
實作從「文件→段落→重點/關鍵詞→語意分群→卡片草稿→統計」的核心演算法/LLM 流程，輸出穩定 JSON，供其他模組使用。

## 範圍
- 段落切分（Markdown/純文字），保留來源索引與標題階層；規則寫死，先不做聰明合併。  
- 重點一句 + 關鍵詞抽取（LLM/embedding 可替換）。  
- 向量化與語意分群：僅用閾值分群（`topicThreshold`，預設 0.75），並可設定 `maxTopics`（預設 5，且至少 1 個主題）。  
- 卡片草稿生成：每主題預設 1 張卡；若 `memberIds.length > 8`，可拆成 2 張卡；每張卡標題 + 1–5 摘要（目標 3–5）。  
- 統計：重點數、主題數、卡片數。  
- 日誌/除錯：可選擇輸出中間結果。

## 輸入/輸出
- Input：原始文字、選項（語言/最大主題數或閾值、每卡摘要數、溫度/seed 等）。  
- Output JSON（穩定 schema，使用 topics 命名，排序 deterministic）：  
  - `paragraphs`: [{id, text, headingLevel?, sectionPath?, idx}]  
  - `keypoints`: [{paragraphId, sentence, keywords[]}]  
  - `topics`: [{id, title, memberIds[], summaryBullets[]}]  
  - `cards`: [{id, topicId, title, bullets[1-5]}]  // 目標 3–5  
  - `stats`: {totalParagraphs, totalKeypoints, totalTopics, totalCards}

## 功能需求
1) 段落切分：依標題/空行/清單，避免過短段落合併；保留 idx。  
2) 重點抽取：每段一句話摘要 + 關鍵詞（1–5），可選 deterministic 模式。  
3) 向量化：可配置模型；暴露維度/批次大小；失敗要回傳可讀錯誤。  
4) 分群：僅用相似度閾值 `topicThreshold`，並尊重 `maxTopics` 上限；至少產生 1 個主題；輸出 memberIds 與代表標題。  
5) 卡片草稿：每主題預設 1 張卡；若 `memberIds.length > 8`，可拆成 2 張卡；每卡 bullets 1–5（目標 3–5）。  
6) 統計：計算重點/主題/卡片數；隨輸出一起返回。  
7) 參數化：溫度、top_p、主題上限/閾值、每卡最大摘要數、max tokens。  
8) 可測性：提供 demo CLI 或函式，能打印中間結果。

## 非功能
- 效能：5k tokens 級別可在合理時間內完成。  
- 錯誤處理：輸入空檔/過長/編碼錯誤要有明確訊息。  
- 可替換：LLM/embedding/聚類實作可抽換，介面固定。

## 驗收標準
- 給定範例檔，輸出 JSON 符合 schema，統計數值正確。  
- 切段、重點抽取主觀滿意度 ≥ 80%。  
- 分群結果可讀，卡片 bullets 1–5 條（目標 3–5）；同一輸入重跑排序一致（topic 依最小段落 idx 由小到大；card 依 topic 順序；stats 一致）。  
- CLI 或單元測試可跑通。

## 風險與緩解
- LLM 漂移：提供 deterministic 設定；允許替換模型。  
- 分群品質：暴露群數/閾值；輸出中間相似度供調試。  
- 成本/時延：控制輸入長度；可分批或降採樣。

