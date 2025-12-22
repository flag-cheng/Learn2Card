## Backend（Agent A）

本模組負責：**純文字字串** → 切段 → 重點/關鍵詞 →（簡易）語意分群 → 卡片草稿 → 輸出符合固定 schema 的 `deck.json`。

### 重要限制（必須遵守）

- **核心管線只接受文字字串**：`learn2cards.analyze_text(text: str, ...)`
- **核心管線不做任何 I/O**（不讀檔、不抓 URL）
- **檔案讀寫只會出現在 CLI**（`backend/cli.py`）

### 安裝（使用 uv）

在專案根目錄：

```bash
cd backend
uv sync
```

### CLI：generate / validate

#### 產生 deck.json

```bash
cd backend
uv run python cli.py generate --input ../try.txt --force
```

- 若未指定 `--output`，預設輸出到：`frontend/public/deck.json`
- 若輸出檔已存在，需要加 `--force` 才會覆寫

#### 驗證 deck.json

```bash
cd backend
uv run python cli.py validate --input ../frontend/public/deck.json
```

### 直接分析文字（不經檔案）

```bash
cd backend
uv run python cli.py analyze --text "這是一段文字。下一段。" --language zh
```

也可用 stdin：

```bash
cd backend
printf "Hello world.\n\nSecond paragraph." | uv run python cli.py analyze --text -
```

### （選配）HTTP API（無外部依賴）

```bash
cd backend
uv run python cli.py serve --host 127.0.0.1 --port 8000
```

- `GET /healthz`
- `POST /analyze`（JSON body: `{"text":"...", "options":{...}}`）




