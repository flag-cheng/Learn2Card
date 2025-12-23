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

### 執行 Demo CLI（輸出 JSON 到 stdout）

```bash
cd backend
uv run python main.py --text "專案目標是把長文轉成一疊可翻閱的卡片，方便快速掌握重點。"
```

常用參數：
- `--topic-threshold`：分群閾值（預設 0.75）
- `--max-topics`：最大主題數（預設 5，至少 1）
- `--max-bullets`：每卡 bullets 上限（1–5，預設 5）
- `--debug`：在 stderr 印出中間統計（不影響 Deck JSON schema）

### 以程式呼叫（不做任何 I/O）

```python
from learn2cards.agent_a import generate_deck

deck = generate_deck("你的文字…")
payload = deck.model_dump()  # 符合 frontend/src/types.ts 的 Deck schema
```



