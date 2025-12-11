# 全局 PRD：文件歸納切卡機（雙 Agent 平行示範）

## 專案目標
- 目的：示範 Cursor（地端）+ Cloud Agent（遠端 GitHub）協作；本機 P0 有 UI shell，可啟動且看到假資料卡片。
- 輸入：Markdown/純文字（暫不含 PDF）。流程：切段 → 每段一句重點 + 關鍵詞 → embedding 粗分群 → LLM 群組命名與寫卡（標題 + 1–5 bullets，目標 3–5）→ 統計段落/主題/卡片 → 輸出 deck.json。
- 角色：A-agent（資料/核心邏輯）與 B-agent（UI 接 JSON）可同時開工、互不等待。

## 既有資產（P0）
- UI shell（本地可啟動，含假內容）。
- 規格文件：PRD、Technical Spec、JSON schema（固定）、deck.sample.json（供 UI 驗收）。
- 無需自動化 GitHub（C-agent）；演示以截圖/文章呈現。

## 範圍內
- 固定的 deck JSON schema（paragraphs/topics/cards/stats 等核心欄位、卡片 bullets 規格）。
- A-agent：CLI `cli generate` 產生 deck.json；`cli validate` 驗證 deck.json（schema + 基本規則）。
- B-agent：將 UI shell 接上 JSON，先用 deck.sample.json，後切換 deck.json；支援翻卡上一張/下一張、分頁或序列瀏覽、統計、主題跳轉、錯誤提示。

## 範圍外
- 帳號/權限/多人協作功能；PDF 解析；精緻動畫；成本最佳化策略。

## 成功指標（MVP）
- 本地啟動 UI shell 成功，以 deck.sample.json 正常翻卡、分頁/序列瀏覽、統計、主題跳轉與錯誤提示。
- A-agent 能以 CLI 讀 Markdown/純文字並輸出符合 schema 的 deck.json；`cli validate` 可驗證。
- JSON schema 穩定，兩 Agent 可並行開發；以同一 schema 接線即能切換 deck.sample.json → deck.json。

## 里程碑
- M1（P0）：UI shell + deck.sample.json + 固定 JSON schema + 文件齊備。
- M2：A-agent 完成 generate/validate CLI，產出 deck.json。
- M3：B-agent UI 接 deck.sample.json 驗收，後切 deck.json 並通過。

## 風險與緩解
- Schema 變動風險：鎖定 schema，任何變更需明示版本與遷移。
- 資料品質：LLM 漂移與分群品質，用 deterministic 設定、暴露群數/閾值；提供 validate 檢查必填欄位/ bullets 數量。
- 平台差異：Windows CRLF/編碼，規定 UTF-8 輸出；行尾一致。

## 驗收
- 以範例 Markdown 產生 deck.json，`cli validate deck.json` 通過。
- UI 以 deck.sample.json 與 deck.json 各跑一輪：翻卡、分頁/序列、統計、主題跳轉、錯誤提示均正常。

