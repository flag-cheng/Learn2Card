# Agent A PRD：核心 NLP/LLM 管線

## 使命
實作從「文件→段落→重點/關鍵詞→語意分群→卡片草稿→統計」的核心演算法/LLM 流程，輸出穩定 JSON，供其他模組使用。

## 範圍
- 段落切分（Markdown/純文字），保留來源索引與標題階層。  
- 重點一句 + 關鍵詞抽取（LLM/embedding 可替換）。  
- 向量化與語意分群（k-means/層次或閾值分群，參數可調）。  
- 卡片草稿生成：每群組 1–n 張卡，標題 + 3–5 摘要。  
- 統計：重點數、主題數、卡片數。  
- 日誌/除錯：可選擇輸出中間結果。

## 輸入/輸出
- Input：原始文字、選項（語言/最大群數或閾值、每卡摘要數、溫度/seed 等）。  
- Output JSON（穩定 schema）：  
  - `paragraphs`: [{id, text, headingLevel?, sectionPath?, idx}]  
  - `keypoints`: [{paragraphId, sentence, keywords[]}]  
  - `clusters`: [{id, title, memberIds[], summaryBullets[]}]  
  - `cards`: [{id, clusterId, title, bullets[3-5]}]  
  - `stats`: {totalParagraphs, totalKeypoints, totalClusters, totalCards}

## 功能需求
1) 段落切分：依標題/空行/清單，避免過短段落合併；保留 idx。  
2) 重點抽取：每段一句話摘要 + 關鍵詞（1–5），可選 deterministic 模式。  
3) 向量化：可配置模型；暴露維度/批次大小；失敗要回傳可讀錯誤。  
4) 分群：支援指定群數或相似度閾值；輸出成員與代表標題。  
5) 卡片草稿：依群組生成 1–n 張卡；每卡 3–5 摘要。  
6) 統計：計算重點/主題/卡片數；隨輸出一起返回。  
7) 參數化：溫度、top_p、群數/閾值、每卡最大摘要數、max tokens。  
8) 可測性：提供 demo CLI 或函式，能打印中間結果。

## 非功能
- 效能：5k tokens 級別可在合理時間內完成。  
- 錯誤處理：輸入空檔/過長/編碼錯誤要有明確訊息。  
- 可替換：LLM/embedding/聚類實作可抽換，介面固定。

## 驗收標準
- 給定範例檔，輸出 JSON 符合 schema，統計數值正確。  
- 切段、重點抽取主觀滿意度 ≥ 80%。  
- 分群結果可讀，卡片 bullets 3–5 條。  
- CLI 或單元測試可跑通。

## 風險與緩解
- LLM 漂移：提供 deterministic 設定；允許替換模型。  
- 分群品質：暴露群數/閾值；輸出中間相似度供調試。  
- 成本/時延：控制輸入長度；可分批或降採樣。

