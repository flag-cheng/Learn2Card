## Backend（Agent A：核心管線）

本目錄已依 `docs/prd/agent-a.md` 實作 **Agent A 核心 NLP/LLM 管線**（以可替換的 heuristic/embedding 先行落地），將「文字字串」轉成穩定 schema 的 JSON：

- 段落切分（Markdown/純文字）
- 每段重點一句 + 關鍵詞（1–5）
- 向量化（預設 `hashing_v1`，可替換）
- 閾值分群（`topicThreshold`，尊重 `maxTopics`，至少 1 topic）
- 卡片草稿（每 topic 1 張；`memberIds > 8` 會拆 2 張；bullets 1–5，目標 3–5）
- 統計（paragraph/keypoint/topic/card 數量）

### 環境與安裝（必須使用 uv）

在 `backend/` 目錄下：

```bash
uv sync
```

### 執行 demo CLI（不做檔案 I/O）

注意：**只接受文字字串**，不接受檔案路徑或 URL。

```bash
uv run python main.py --text $'## 標題\n\n這是一段文字...\n- 清單項目 A\n- 清單項目 B' --debug
```

輸出為符合 schema 的 deterministic JSON（key 排序固定）。




