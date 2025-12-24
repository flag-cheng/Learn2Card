## Backend（Agent A）

本模組提供 **FastAPI HTTP API** 與核心處理管線：

- **Endpoint**：`POST /api/process`
- **輸入**：只接受 JSON 的 `text` 純文字字串（不做檔案讀取、不做 URL 抓取）
- **輸出**：固定寫入 `frontend/public/deck.json`（UTF-8、無 BOM、JSON 縮排 2、`ensure_ascii=false`）
- **CORS**：允許 `http://localhost:5173`、`http://127.0.0.1:5173`

### 安裝依賴（使用 uv）

在專案根目錄執行：

```bash
cd backend
uv sync
```

### 啟動 API Server

```bash
cd backend
uv run uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

### 呼叫 API（範例）

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/process" \
  -H "Content-Type: application/json" \
  -d '{"text":"# 標題\n\n第一段。\n\n- 清單項目","topic_threshold":0.75,"max_topics":5,"max_bullets":5,"debug":true}'
```

成功後會在專案根目錄下產生/覆寫：

- `frontend/public/deck.json`

###（可選）CLI 快速產生 deck.json

```bash
cd backend
uv run python main.py --text "# 標題\n\n第一段。\n\n- 清單項目" --debug
```

### 錯誤處理

- `text` 為空：回傳 **HTTP 400**，並提供清楚錯誤訊息
- 內部錯誤：回傳 **HTTP 500**



