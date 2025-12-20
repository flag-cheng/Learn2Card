## Backend（預留）

- 這裡將放置 Cloud Agent / API / 推論邏輯相關的程式碼與設定。
- 已加入 **Agent A（CLI + demo 核心流程）**：切段 → 每段一句重點 + 關鍵詞 → 向量化 → 閾值分群 → 產生卡片草稿 → 統計 → 輸出 `deck.json`。

## API（用於 UI 上傳檔案即時產生卡片）

啟動後端（預設 `http://localhost:8000`）：

```bash
python3 -m pip install -U fastapi "uvicorn[standard]" python-multipart
python3 -m uvicorn backend.main:app --reload --port 8000
```

前端上傳 Markdown/純文字後，會呼叫 `POST /api/generate`，後端回傳 deck JSON（schema `1.0.0`），UI 會立即渲染卡片。

## CLI 用法（Agent A）

在 repo 根目錄執行：

```bash
./cli generate --input docs/prd/agent-a.md --force
./cli validate --input frontend/public/deck.json
```

預設 `generate` 會輸出到 `frontend/public/deck.json`（可用 `--output` 改路徑；若檔案已存在需加 `--force`）。

> 說明：此版本為 **deterministic demo 實作**，不依賴外部 LLM/embedding 服務；但保留了 `--model` / `--temperature` / `--top-p` 等參數以符合規格的可替換介面。



