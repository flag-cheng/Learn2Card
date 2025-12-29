## Backend（預留）

- 這裡將放置 Cloud Agent / API / 推論邏輯相關的程式碼與設定。
- 已加入 **Agent A（CLI + demo 核心流程）**：切段 → 每段一句重點 + 關鍵詞 → 向量化 → 閾值分群 → 產生卡片草稿 → 統計 → 輸出 `deck.json`。

## CLI 用法（Agent A）

在 repo 根目錄執行：

```bash
./cli generate --input docs/prd/agent-a.md --force
./cli validate --input frontend/public/deck.json
```

預設 `generate` 會輸出到 `frontend/public/deck.json`（可用 `--output` 改路徑；若檔案已存在需加 `--force`）。

> 說明：此版本為 **deterministic demo 實作**，不依賴外部 LLM/embedding 服務；但保留了 `--model` / `--temperature` / `--top-p` 等參數以符合規格的可替換介面。


感覺需要更多的實作，或是更難的實作，因為目前都是用簡單的切字邏輯處理
如果要進行遷入化等處理，會相對來說更好。
