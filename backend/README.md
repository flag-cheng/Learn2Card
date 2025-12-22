## Backend（Agent A）

本目錄實作 Agent A 的核心流程：**純文字 → 段落切分 → 重點/關鍵詞 → 語意分群 → 卡片草稿 → `deck.json`**。

### 安裝依賴（必須使用 uv）

在專案根目錄：

```bash
cd backend
uv sync
```

### CLI：generate / validate

> 注意：**核心管線只吃文字字串**；讀檔/寫檔屬於 CLI 外層行為（符合 PRD 限制）。

產生 `deck.json`（預設輸出到 `frontend/public/deck.json`）：

```bash
cd backend
uv run cli generate --input ../docs/prd/agent-a.md --force
```

驗證 deck JSON：

```bash
cd backend
uv run cli validate --input ../frontend/public/deck.json
```

### API：/analyze

啟動 API（供前端整合呼叫）：

```bash
cd backend
uv run uvicorn learn2cards.api:app --host 0.0.0.0 --port 8000
```

- `GET /health`
- `POST /analyze`（body: `{ "text": "...", "source": "text", "options": {...} }`）



