## Backend（Agent A：核心 NLP/LLM 管線）

本目錄提供 Agent A 的核心邏輯：**純文字** → 段落切分 → 摘要/關鍵詞 → 向量化 → 閾值分群 → 卡片草稿 → 輸出 Deck JSON。

重要限制（符合 `docs/prd/agent-a.md`）：
- **輸入僅接受文字字串**（不接受檔案路徑 / URL）
- **核心管線不做任何檔案讀取/網路抓取 I/O**

### 安裝（必須使用 uv）

在專案根目錄：

```bash
cd backend
uv sync
```

### 執行 CLI（對外介面）

#### 基本用法（固定輸出到 `frontend/public/deck.json`）

```bash
cd backend
uv run python main.py --text "專案目標是把長文轉成一疊可翻閱的卡片，方便快速掌握重點。"
```

執行後會自動產生 `frontend/public/deck.json`，前端可直接使用。

#### 從專案根目錄執行（Agent B 會使用此格式）

```bash
cd backend && uv run python main.py --text "專案目標是把長文轉成一疊可翻閱的卡片，方便快速掌握重點。"
```

#### 參數說明

**必要參數**：
- `--text`：輸入純文字字串（必填）

**可選參數**：
- `--topic-threshold`：分群閾值（預設 0.75，範圍 0.0–1.0）
- `--max-topics`：最大主題數（預設 5，最小 1）
- `--max-bullets`：每卡 bullets 上限（預設 5，範圍 1–5）
- `--debug`：在 stderr 顯示統計資訊

#### 執行結果

**成功時**：
- 產生檔案：`frontend/public/deck.json`
- Exit code：0
- stderr 顯示：
  ```
  ✓ 已成功輸出到：<路徑>/frontend/public/deck.json
    - 段落數：N
    - 主題數：N
    - 卡片數：N
  ```

**失敗時**：
- Exit code：非 0
- stderr 顯示錯誤訊息

#### 注意事項
- 輸出檔案使用 UTF-8 編碼，確保中文等多語言內容正確顯示
- 若 `frontend/public/` 目錄不存在，會自動建立
- 每次執行會覆寫 `deck.json`（不累加、不備份）
- **輸出位置固定**，不支援自訂路徑或 stdout 輸出

### 以程式呼叫（不做任何 I/O）

```python
from learn2cards.agent_a import generate_deck

deck = generate_deck("你的文字…")
payload = deck.model_dump()  # 符合 frontend/src/types.ts 的 Deck schema
```



