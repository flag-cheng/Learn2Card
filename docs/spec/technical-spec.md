# Technical Spec：文件歸納切卡機（雙 Agent 平行）

## 架構概覽
- 入口：Markdown/純文字檔。
- A-agent：CLI 工具（generate / validate），產出 `deck.json` 符合固定 schema。
- B-agent：UI shell（已存在 P0），改為讀取 JSON（先 `deck.sample.json`，後 `deck.json`），提供翻卡/分頁/統計/主題跳轉/錯誤提示。
- 無 C-agent；GitHub 操作以截圖/文章示範。

## JSON Schema（固定）
檔名：`deck.json` / `deck.sample.json`，UTF-8，CRLF/ LF 皆可，建議 LF。

```json
{
  "meta": {
    "source": "string",              // 輸入檔案名或 URL
    "generatedAt": "ISO8601 string", // 產出時間
    "schemaVersion": "1.0.0"
  },
  "paragraphs": [
    {
      "id": "p1",
      "idx": 0,                      // 原文序號
      "text": "string",
      "headingLevel": 1,             // 可選，對應 Markdown 標題
      "sectionPath": ["H1", "H2"]    // 可選，層級路徑
    }
  ],
  "keypoints": [
    {
      "paragraphId": "p1",
      "sentence": "string",          // 該段的一句重點
      "keywords": ["k1", "k2"]       // 1–5 個關鍵詞
    }
  ],
  "topics": [
    {
      "id": "t1",
      "title": "string",             // 群組命名
      "memberIds": ["p1", "p2"],     // 所含段落 id
      "summaryBullets": ["..."]      // 可選，用於群組概覽
    }
  ],
  "cards": [
    {
      "id": "c1",
      "topicId": "t1",
      "title": "string",
      "bullets": ["b1", "b2", "b3"]  // 1–5 條，目標 3–5
    }
  ],
  "stats": {
    "totalParagraphs": 0,
    "totalKeypoints": 0,
    "totalTopics": 0,
    "totalCards": 0
  }
}
```

必要規則：
- `topics.memberIds` 需對應 `paragraphs.id`；`cards.topicId` 需對應 `topics.id`。
- `bullets` 長度 1–5，目標 3–5。
- `stats` 與實際數量一致（可由 validate 計算驗證）。

## A-agent：CLI 介面
- 命令：`cli generate --input <path> --output <path> [--max-topics N] [--temperature x] [--cluster-threshold y] [--model <name>] [--language zh|en|auto]`
  - 讀 Markdown/純文字，完成：切段→重點+關鍵詞→embedding 粗分群→LLM 群組命名/寫卡→統計→輸出 deck.json。
  - 預設行為：若 output 未指定，寫入同目錄 `deck.json`；若檔已存在，需警示（可用 `--force` 覆寫）。
- 命令：`cli validate --input <path>`
  - 驗證 JSON schema、必填欄位、鍵的對應關係、bullets 範圍、stats 正確性。
  - 若失敗，回傳錯誤清單；成功則回傳 OK。
- 日誌：至少 console；`--verbose` 可輸出中間結果（分群、卡片摘要）。
- 錯誤處理：輸入不存在/超過大小/編碼錯誤，需友善訊息。

## B-agent：UI 整合需求
- 資料來源：優先讀取 `deck.sample.json`（P0 已放），驗收後可切換 `deck.json`。
- 載入方式：前端 fetch 本地 JSON 檔或由簡易 dev server 提供；需有載入中/錯誤提示。
- 功能：
  - 翻卡：上一張/下一張；支援鍵盤左右鍵。
  - 分頁或序列瀏覽：可設定每頁卡片數，或單張序列模式。
  - 統計：顯示 stats（重點/主題/卡片數）。
  - 主題跳轉：依 topic 篩選/跳轉。
  - 錯誤提示：JSON 格式錯、缺欄位、找不到檔案時顯示。
- Schema 綁定：前端依固定 schema 解析；若字段缺失要有 fallback 或提示。

## 資料流程（平行開發）
- A-agent：根據 schema 與 sample，先做 validate，再做 generate；不依賴 UI。
- B-agent：以 `deck.sample.json` 為假資料完成 UI；完成後只需切換檔案路徑即可驗收 `deck.json`。
- Schema 版本固定為 1.0.0；若要改版，需在文件中明示並提供遷移指引。

## 驗收標準
- A-agent：`cli generate` 對範例 Markdown 產出合法 `deck.json`，`cli validate deck.json` 通過；stats 數值正確；bullets 1–5 條（目標 3–5）。
- B-agent：以 `deck.sample.json` 能翻卡、分頁/序列瀏覽、統計、主題跳轉、錯誤提示；切換為 `deck.json` 時仍正常。
- 整體：專案在無 LLM/解析時也能啟動（使用 sample），符合示範目的。

