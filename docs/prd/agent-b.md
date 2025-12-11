# Agent B PRD：Web 翻卡介面

## 使命
提供簡單 Web 介面載入 Agent A 的 JSON 輸出，支援分頁/序列翻卡、主題瀏覽與統計展示，作為示範用的可視化大綱。

## 範圍
- 資料載入：本地檔或 API endpoint，JSON schema 與 Agent A 對齊；demo 版以 `fetch('/deck.json')` 讀取放在 public 根目錄的輸出。  
- 卡片呈現：標題 + 1–5 摘要（目標 3–5），上一張/下一張、分頁控制、鍵盤左右鍵。  
- 統計區：重點/主題/卡片數。  
- 主題瀏覽：依 topic 跳轉或篩選。  
- 錯誤提示：資料格式錯誤或載入失敗的提示。

## 資料介面（JSON）
- `cards`: [{id, topicId, title, bullets[]}]  
- `topics`: [{id, title, memberIds[]}]  
- `stats`: {totalKeypoints, totalTopics, totalCards}  
- 可附帶 `paragraphs` / `keypoints` 以備後續顯示。

## 功能需求
1) 載入：檔案選擇或輸入 URL；顯示載入中狀態。  
2) 導航：上一張/下一張；分頁（例如每頁 N 張）；鍵盤左右鍵快捷。  
3) 主題跳轉：依 topic 過濾/跳轉，顯示主題標題。  
4) 統計展示：同步顯示重點/主題/卡片數。  
5) 錯誤處理：JSON schema 驗證，提供可讀提示。  
6) UI：簡潔、可讀，行高、對比度足夠。

## 非功能
- 相容 Chrome/Edge；支援 Windows 本地開啟。  
- 可純前端（靜態檔）或簡單本地 server；不強依賴後端。  
- 大檔載入要有 loading/空狀態，避免長時間白屏。

## 驗收標準
- 能載入範例 JSON 並正常翻卡、分頁、群組跳轉。  
- 統計數據與 JSON 一致；錯誤 JSON 能顯示提示。  
- 主要操作可被示範（滑鼠/鍵盤）。

## 風險與緩解
- JSON 版本差異：固定 schema，必要時增加向後相容映射。  
- 大檔渲染：使用分頁/虛擬列表策略，顯示 loading。  
- 瀏覽器差異：優先桌面 Chrome/Edge。

