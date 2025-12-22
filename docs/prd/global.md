# 全局 PRD：文件歸納切卡機（雙 Agent 平行示範）

## 本 PRD 的角色
**本 PRD（global.md）負責整合 Agent A 和 Agent B 的實作結果**，具體任務包括：
1. **分支整合**：將 Agent A 和 Agent B 各自由 Cloud Agent 自動產生的開發分支 merge，產生新的整合分支（不直接動到 master）
2. **流程驗證**：在整合分支上確保完整的「上傳 → 後端分析 → 即時出卡」流程正常運作
3. **端對端測試**：驗證前後端整合無誤，使用者可以上傳文件並看到生成的卡片
4. **分支資訊**：Agent A 和 Agent B 的分支名稱由 Cloud Agent 自動產生，將在實作完成後提供

## 專案目標
- 目的：示範 Cursor（地端）+ Cloud Agent（遠端 GitHub）協作；本機 P0 有 UI shell，可啟動且看到假資料卡片。
- 輸入：Markdown/純文字（暫不含 PDF）。流程：切段 → 每段一句重點 + 關鍵詞 → embedding 粗分群 → LLM 群組命名與寫卡（標題 + 1–5 bullets，目標 3–5）→ 統計段落/主題/卡片 → 輸出 deck.json。
- 角色：A-agent（資料/核心邏輯）與 B-agent（UI 接 JSON）可同時開工、互不等待。

## 既有資產（P0）
- UI shell（本地可啟動，含假內容）。
- 規格文件：PRD、Technical Spec、JSON schema（固定）、deck.sample.json（供 UI 驗收）。
- 無需自動化 GitHub（C-agent）；演示以截圖/文章呈現。

## 範圍內
- 固定的 deck JSON schema（paragraphs/topics/cards/stats 等核心欄位、卡片 bullets 規格）；demo 輸出放 public 根目錄 `deck.json`，UI 以 `fetch('/deck.json')` 讀取。
- **A-agent（後端）**：CLI `cli generate` 產生 deck.json；`cli validate` 驗證 deck.json（schema + 基本規則）；提供 API 端點供前端呼叫。
- **B-agent（前端）**：將 UI shell 接上 JSON，先用 deck.sample.json，後切換 deck.json；支援翻卡上一張/下一張、分頁或序列瀏覽、統計、主題跳轉、錯誤提示；提供檔案上傳功能。
- **整合任務（本 PRD）**：
  - Merge Agent A 和 Agent B 的開發分支，產生新的整合分支
  - 建立前後端 API 連接（前端呼叫後端分析服務）
  - 確保「上傳 → 後端分析 → 即時出卡」的完整流程運作
  - 處理可能的整合問題（CORS、API 格式、錯誤處理等）
  - 驗證通過後再考慮 merge 到 master

## 範圍外
- 帳號/權限/多人協作功能；PDF 解析；精緻動畫；成本最佳化策略。

## 成功指標（MVP）
- 本地啟動 UI shell 成功，以 deck.sample.json 正常翻卡、分頁/序列瀏覽、統計、主題跳轉與錯誤提示。
- A-agent 能以 CLI 讀 Markdown/純文字並輸出符合 schema 的 deck.json；`cli validate` 可驗證。
- JSON schema 穩定，兩 Agent 可並行開發；以同一 schema 接線即能切換 deck.sample.json → deck.json。

## 里程碑
- M1（P0）：UI shell + deck.sample.json + 固定 JSON schema + 文件齊備。✅
- M2：A-agent 完成 generate/validate CLI，產出 deck.json。（由 Cloud Agent 在獨立分支實作）
- M3：B-agent UI 接 deck.sample.json 驗收，後切 deck.json 並通過。（由 Cloud Agent 在獨立分支實作）
- **M4（整合）**：Merge A/B 分支到新的整合分支，前後端整合，完整流程驗證。（本 PRD 負責此階段）
- **M5（發布）**：整合分支驗收通過後，merge 到 master。（視情況執行）

## 風險與緩解
- **Schema 變動風險**：鎖定 schema，任何變更需明示版本與遷移。
- **資料品質**：LLM 漂移與分群品質，用 deterministic 設定、暴露群數/閾值；提供 validate 檢查必填欄位/ bullets 數量。
- **平台差異**：Windows CRLF/編碼，規定 UTF-8 輸出；行尾一致。
- **整合風險**：
  - 分支衝突：Agent A 和 Agent B 可能修改相同檔案，在整合分支上需仔細 review 並解決 merge conflicts
  - API 不匹配：前後端 API 格式可能不一致，需在整合分支上檢查並調整 request/response 格式
  - CORS 問題：前端呼叫後端可能遇到跨域問題，需在後端設定適當的 CORS headers
  - 環境差異：確保前後端都能在 Windows 本地環境正常啟動（在整合分支上測試）
  - 非同步處理：後端分析可能耗時較長，前端需要適當的 loading 狀態與錯誤處理
  - 整合分支隔離：在整合分支上完成所有測試後，再 merge 到 master，避免破壞 master 的穩定性

## 驗收標準

### Agent A 驗收（M2）
- 以範例 Markdown 產生 deck.json，`cli validate deck.json` 通過。
- 輸出的 JSON 符合固定 schema，統計數值正確。

### Agent B 驗收（M3）
- UI 以 deck.sample.json 與 deck.json 各跑一輪：翻卡、分頁/序列、統計、主題跳轉、錯誤提示均正常。
- 能上傳 .txt 或 .md 檔案，或貼上純文字。

### 整合驗收（M4 - 本 PRD 負責）
- **分支整合成功**：Agent A 和 Agent B 的分支已 merge 到新的整合分支，無衝突或衝突已解決。
- **完整流程驗證**（在整合分支上執行）：
  1. 在前端上傳 .txt 或 .md 檔案（或貼上純文字）
  2. 前端呼叫 Agent A 的後端 API 進行分析
  3. 後端返回 JSON 結果
  4. 前端即時顯示生成的卡片
  5. 可以正常翻卡、切換主題、查看統計
- **端對端測試**：使用真實的 Markdown 文件測試，從上傳到顯示卡片的完整流程無誤。
- **錯誤處理**：上傳錯誤格式檔案、後端處理失敗等異常情況都有清楚提示。
- **準備 merge 到 master**：所有驗收通過後，整合分支可以安全地 merge 到 master。

