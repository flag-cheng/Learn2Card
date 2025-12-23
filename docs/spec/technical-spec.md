# Technical Spec：文件歸納切卡機（雙 Agent 平行）

## 架構概覽
- **輸入**：Markdown/純文字檔（`.md` 或 `.txt`）
- **Agent A（Backend）**：
  - 程式位置：`backend/main.py`
  - 執行方式：CLI（`uv run python main.py --text "..."`）
  - 固定輸出到：`frontend/public/deck.json`
  - **不提供 HTTP API**（採用簡易 Demo 版）
- **Agent B（Frontend）**：
  - React + TypeScript + Vite
  - 從 `public/deck.json` 載入卡片資料
  - 提供檔案上傳、指令產生、重新載入功能
  - 支援翻卡、分頁、統計、主題跳轉
- **整合方式**：上傳檔案 → 產生指令 → 手動執行 Backend → 重新載入 → 顯示卡片
- **無 C-agent**；GitHub 操作以截圖/文章示範

## JSON Schema（固定版本：與 frontend/src/types.ts 完全一致）

檔名：`deck.json`  
位置：`frontend/public/deck.json`  
編碼：UTF-8（無 BOM）  
格式：JSON（縮排 2 空格）

```typescript
// 與 frontend/src/types.ts 的 Deck 型別完全一致
interface Deck {
  paragraphs: Paragraph[];
  topics: Topic[];
  cards: Card[];
  stats: DeckStats;
}

interface Paragraph {
  id: string;           // 格式：p1, p2, p3, ...
  text: string;         // 原始段落文字
  summary: string;      // 一句話摘要（≤60字）
  keywords: string[];   // 1–5 個關鍵詞
  sourceIndex: number;  // 原文中的順序索引（從 0 開始）
}

interface Topic {
  id: string;           // 格式：t1, t2, t3, ...
  title: string;        // 主題標題（從關鍵詞或摘要中選取）
  memberIds: string[];  // 所含 paragraph 的 id 陣列
}

interface Card {
  id: string;           // 格式：c1, c2, c3, ...
  topicId: string;      // 對應的 topic id
  title: string;        // 卡片標題
  bullets: string[];    // 1–5 條要點（目標 3–5）
}

interface DeckStats {
  paragraphCount: number;  // 段落總數
  topicCount: number;      // 主題總數
  cardCount: number;       // 卡片總數
}
```

### JSON Schema 範例

```json
{
  "paragraphs": [
    {
      "id": "p1",
      "text": "專案目標是把長文轉成一疊可翻閱的卡片，方便快速掌握重點。",
      "summary": "專案目標是把長文轉成一疊可翻閱的卡片，方便快速掌握重點。",
      "keywords": ["專案目標", "長文", "卡片", "快速掌握", "重點"],
      "sourceIndex": 0
    }
  ],
  "topics": [
    {
      "id": "t1",
      "title": "專案目標",
      "memberIds": ["p1"]
    }
  ],
  "cards": [
    {
      "id": "c1",
      "topicId": "t1",
      "title": "專案目標",
      "bullets": [
        "專案目標是把長文轉成一疊可翻閱的卡片，方便快速掌握重點。",
        "關鍵詞：專案目標, 長文, 卡片, 快速掌握, 重點"
      ]
    }
  ],
  "stats": {
    "paragraphCount": 1,
    "topicCount": 1,
    "cardCount": 1
  }
}
```

### 必要規則

1. **ID 格式**：
   - Paragraph: `p1`, `p2`, `p3`, ...（從 1 開始）
   - Topic: `t1`, `t2`, `t3`, ...（從 1 開始）
   - Card: `c1`, `c2`, `c3`, ...（從 1 開始）

2. **關聯性**：
   - `topics[].memberIds` 必須對應存在的 `paragraphs[].id`
   - `cards[].topicId` 必須對應存在的 `topics[].id`

3. **數量限制**：
   - `paragraphs[].keywords`：1–5 個
   - `cards[].bullets`：1–5 條（目標 3–5）
   - `topics`：至少 1 個，預設最多 5 個（可透過 `--max-topics` 調整）

4. **統計一致性**：
   - `stats.paragraphCount` = `paragraphs.length`
   - `stats.topicCount` = `topics.length`
   - `stats.cardCount` = `cards.length`

5. **排序規則（Deterministic）**：
   - Topics 依其 `memberIds` 中最小的 `sourceIndex` 由小到大排序
   - Cards 依其 `topicId` 對應的 topic 順序排序
   - 同一輸入重跑，排序必須一致

6. **卡片生成規則**：
   - 每個 topic 預設生成 1 張卡片
   - 若 `memberIds.length > 8`，拆成 2 張卡片（標題加「（上）」「（下）」）
   - 每張卡片的 bullets 從該 topic 的段落摘要中提取

7. **分群規則**：
   - 使用相似度閾值分群（預設 `topicThreshold = 0.75`）
   - 尊重 `maxTopics` 上限（預設 5）
   - 至少產生 1 個 topic

## Agent A：Backend CLI 介面規範

### 程式位置與執行方式

**程式位置**：`backend/main.py`（相對於專案根目錄）

**執行指令**：
```bash
# 從 backend 目錄執行
cd backend
uv run python main.py --text "輸入的純文字內容"

# 從專案根目錄執行（Agent B 會使用此格式）
cd backend && uv run python main.py --text "輸入的純文字內容"
```

### 必要參數

- `--text <string>`：輸入的純文字字串（**必填**）
  - 接受 Markdown 或純文字格式
  - 不接受檔案路徑或 URL
  - 由呼叫方（Agent B）負責檔案讀取

### 可選參數

- `--topic-threshold <float>`：分群閾值（預設 0.75，範圍 0.0–1.0）
- `--max-topics <int>`：最大主題數（預設 5，最小 1）
- `--max-bullets <int>`：每卡摘要數上限（預設 5，範圍 1–5）
- `--debug`：在 stderr 顯示除錯訊息與統計資訊

### 輸出行為

**固定輸出位置**：`frontend/public/deck.json`（相對於專案根目錄）

**輸出格式**：
- 編碼：UTF-8（無 BOM）
- 格式：JSON（縮排 2 空格，`ensure_ascii=False`, `sort_keys=True`）
- Schema：完全符合 `frontend/src/types.ts` 的 `Deck` 型別

**執行結果**：
- 成功時：
  - Exit code：0
  - 自動建立 `frontend/public/` 目錄（若不存在）
  - 覆寫 `deck.json`（不累加、不備份）
  - stderr 輸出：
    ```
    ✓ 已成功輸出到：<絕對路徑>/frontend/public/deck.json
      - 段落數：N
      - 主題數：N
      - 卡片數：N
    ```
- 失敗時：
  - Exit code：非 0
  - stderr 輸出：明確的錯誤訊息

### 處理流程

1. **段落切分**：依標題（`#`）、空行、清單項目切分
2. **摘要與關鍵詞**：每段生成一句話摘要（≤60字）+ 1–5 個關鍵詞
3. **向量化**：使用 embedding（預設為 deterministic hashing，可替換）
4. **相似度分群**：閾值分群（`topicThreshold`），尊重 `maxTopics` 上限
5. **主題命名**：從關鍵詞或摘要中選取最具代表性的標題
6. **卡片生成**：每主題 1 張卡（memberIds > 8 則 2 張），bullets 1–5 條
7. **統計計算**：paragraphCount、topicCount、cardCount
8. **JSON 輸出**：寫入 `frontend/public/deck.json`

### 錯誤處理

- 輸入為空：`ValueError: 輸入為空：請提供非空的純文字字串。`
- 輸入過長：`ValueError: 輸入過長：目前上限為 N 字元，實際為 M。`
- 無法切分段落：`ValueError: 無法切分出任何段落：請確認輸入文字內容。`

### 不得實作的功能

- ❌ 不得提供 `--output` 或 `-o` 參數（輸出位置固定）
- ❌ 不得支援 stdout 輸出或管道操作
- ❌ 不得提供自訂輸出路徑功能
- ❌ 不得實作 HTTP API server
- ❌ 不得在核心管線中處理輸入檔案讀取、URL 抓取或其他輸入 I/O

## Agent B：Frontend 整合規範

### 技術棧

- React 18 + TypeScript
- Vite 5
- 套件管理：npm

### 資料來源

**初始載入**：
- 從 `public/deck.json` 讀取預設範例資料
- 需先將 `frontend/src/sampleDeck.ts` 轉存為 `public/deck.json`
- 使用 `fetch('/deck.json')` 讀取

**資料流**：
```
初始化 → fetch('/deck.json') → 顯示範例卡片
     ↓
使用者上傳檔案 → FileReader 讀取內容 → 產生 Backend 指令
     ↓
使用者複製指令 → 手動執行 Backend → Backend 更新 deck.json
     ↓
使用者點擊「重新載入」 → fetch('/deck.json') → 顯示新卡片
```

### 必要功能

1. **檔案上傳**：
   - 只接受 `.txt` 和 `.md` 檔案
   - 使用 `<input type="file" accept=".txt,.md">`
   - 使用 FileReader API 讀取內容為純文字字串（UTF-8）
   - 檔案格式驗證：非 txt/md 顯示錯誤提示

2. **文字輸入**：
   - 提供多行文字輸入框（`<textarea>`）
   - 讓使用者直接貼上純文字內容

3. **Backend 參數輸入介面**：
   - 提供 UI 元件讓使用者調整以下參數：
     - **分群閾值**（`--topic-threshold`）：
       - 預設：0.75
       - 範圍：0.0–1.0（步進 0.05）
       - 建議 UI：滑桿 + 數字顯示
     - **最大主題數**（`--max-topics`）：
       - 預設：5
       - 範圍：1–10
       - 建議 UI：數字輸入框或下拉選單
     - **每卡摘要數**（`--max-bullets`）：
       - 預設：5
       - 範圍：1–5
       - 建議 UI：數字輸入框或下拉選單
     - **除錯模式**（`--debug`）：
       - 預設：false
       - 建議 UI：勾選框（checkbox）
   - 所有參數都應有明確的說明文字
   - 所有參數都應有預設值，使用者可選擇性修改
   - 參數驗證：超出範圍時顯示錯誤並使用預設值

4. **指令產生**：
   - 將使用者輸入的文字進行跳脫處理（處理引號、換行、特殊字元）
   - 根據使用者選擇的參數組裝可執行的指令字串：
     ```bash
     cd backend && uv run python main.py --text "使用者的文字內容" --topic-threshold 0.75 --max-topics 5 --max-bullets 5
     ```
   - 如果參數使用預設值，可省略該參數（Backend 會自動使用預設值）
   - 如果勾選除錯模式，在指令最後加上 `--debug`
   - 顯示在畫面上供使用者查看

5. **複製指令**：
   - 提供「複製指令」按鈕
   - 點擊後複製完整指令（含所有參數）到剪貼簿（使用 `navigator.clipboard.writeText()`）
   - 顯示複製成功提示

6. **執行提示**：
   - 顯示明確的操作步驟：
     ```
     1. 點擊「複製指令」
     2. 開啟終端
     3. 貼上並執行指令
     4. 執行完成後，點擊下方「重新載入卡片」按鈕
     ```

7. **重新載入**：
   - 提供「重新載入卡片」按鈕
   - 點擊後重新執行 `fetch('/deck.json')`
   - 解析 JSON 並更新顯示

8. **卡片瀏覽**：
   - 上一張/下一張按鈕
   - 鍵盤左右鍵快捷
   - 分頁或序列瀏覽模式

9. **統計展示**：
   - 顯示 `stats.paragraphCount`、`stats.topicCount`、`stats.cardCount`

10. **主題跳轉**：
   - 依 topic 篩選或跳轉卡片

11. **錯誤處理**：
    - 檔案格式錯誤提示
    - JSON 解析失敗提示
    - `fetch` 失敗提示（檔案不存在）
    - 空內容提示

### 不得實作的功能

- ❌ 不得提供 URL 輸入欄位
- ❌ 不得實作網頁抓取、爬蟲功能
- ❌ 不得支援 PDF、DOCX 等其他檔案格式
- ❌ 不得從 `sampleDeck.ts` 動態讀取資料（應從 `public/deck.json` 讀取）
- ❌ 不得在前端直接處理文字分析邏輯（必須透過 Backend）
- ❌ 不得嘗試在瀏覽器中執行系統指令
- ❌ 不得實作 HTTP API 呼叫（採用簡易 Demo 版）

## 資料流程（平行開發）

### 開發階段

- **Agent A**：根據 schema 獨立實作 CLI，輸出到 `frontend/public/deck.json`
- **Agent B**：先將 `sampleDeck.ts` 轉存為 `public/deck.json`，以此為假資料完成 UI
- **Schema 固定**：兩 Agent 可同時開發，透過固定的 `deck.json` 介面對接

### 整合階段

1. Merge Agent A 和 Agent B 的開發分支
2. 驗證 `public/deck.json` 初始資料存在
3. 測試完整流程：上傳 → 產生指令 → 執行 Backend → 重新載入 → 顯示卡片
4. 驗證 JSON schema 一致性、編碼正確性、路徑正確性

## 驗收標準

### Agent A 驗收（M2）

- ✅ 程式位置：`backend/main.py` 存在且可執行
- ✅ 執行測試：`cd backend && uv run python main.py --text "範例文字..."` 成功
- ✅ 輸出驗證：
  - 自動產生 `frontend/public/deck.json`
  - JSON 格式符合 `frontend/src/types.ts` 的 `Deck` 型別
  - 包含完整欄位：paragraphs、topics、cards、stats
  - UTF-8 編碼，中文無亂碼
- ✅ Exit code：成功時 0，失敗時非 0
- ✅ 統計正確：stats 數值與實際數量一致
- ✅ 排序一致：同一輸入重跑，topic/card 順序相同

### Agent B 驗收（M3）

- ✅ 初始載入：`public/deck.json` 存在，啟動時正常顯示卡片
- ✅ 卡片瀏覽：翻卡、分頁、統計、主題跳轉功能正常
- ✅ 檔案上傳：能上傳 `.txt` 或 `.md` 檔案，讀取內容為純文字
- ✅ 文字輸入：能在文字框貼上純文字
- ✅ 參數輸入：提供分群閾值、最大主題數、每卡摘要數、除錯模式的輸入介面
- ✅ 參數預設值：所有參數都有明確的預設值顯示
- ✅ 參數驗證：參數範圍驗證正確，超出範圍時顯示提示
- ✅ 指令產生：能根據使用者選擇的參數產生正確的 Backend 執行指令（含跳脫字元處理）
- ✅ 複製功能：「複製指令」按鈕能複製完整指令（含所有參數）到剪貼簿
- ✅ 重新載入：「重新載入卡片」按鈕能重新載入並顯示
- ✅ 錯誤處理：上傳非 txt/md 檔案時顯示錯誤訊息

### 整合驗收（M4）

- ✅ 分支整合：Agent A 和 Agent B 分支已 merge，無衝突或已解決
- ✅ 初始資料：`frontend/public/deck.json` 存在，Frontend 能正常顯示
- ✅ Backend 獨立測試：執行 Backend 指令能成功更新 `deck.json`
- ✅ Frontend 獨立測試：能上傳檔案、產生指令、複製、重新載入
- ✅ 端對端測試：
  1. Frontend 啟動，顯示初始範例卡片
  2. 上傳 `.md` 檔案（或貼上文字）
  3. 複製 Frontend 產生的指令
  4. 到終端執行該指令
  5. Backend 執行成功（exit code 0）並更新 `deck.json`
  6. 回到 Frontend 點擊「重新載入卡片」
  7. 新卡片正確顯示，可翻卡、查看統計
- ✅ 錯誤處理：各種異常情況都有清楚提示

## 技術細節

### 編碼與格式

- **檔案編碼**：UTF-8（無 BOM）
- **換行符號**：LF（建議），Windows CRLF 也支援
- **JSON 格式**：縮排 2 空格，`ensure_ascii=False`，`sort_keys=True`

### UI 介面範例（Agent B 參數輸入）

建議的參數輸入介面佈局：

```
┌─────────────────────────────────────┐
│ 📄 上傳檔案或輸入文字                │
├─────────────────────────────────────┤
│ [選擇檔案] 或 [文字輸入框]           │
│                                     │
│ ⚙️ Backend 處理參數（可選）          │
├─────────────────────────────────────┤
│ 分群閾值: [====●====] 0.75         │
│          (數值越高分群越細)          │
│                                     │
│ 最大主題數: [5 ▼] (1-10)           │
│                                     │
│ 每卡摘要數: [5 ▼] (1-5)            │
│                                     │
│ □ 除錯模式 (顯示詳細處理資訊)       │
│                                     │
│ [產生指令]                          │
├─────────────────────────────────────┤
│ 📋 執行指令：                        │
│ cd backend && uv run python ...     │
│                                     │
│ [複製指令] [重新載入卡片]           │
└─────────────────────────────────────┘
```

### 指令組裝邏輯（Agent B）

```typescript
function generateCommand(
  text: string,
  topicThreshold: number = 0.75,
  maxTopics: number = 5,
  maxBullets: number = 5,
  debug: boolean = false
): string {
  const escapedText = escapeShellArg(text);
  let command = `cd backend && uv run python main.py --text "${escapedText}"`;
  
  // 只有當參數不是預設值時才加入
  if (topicThreshold !== 0.75) {
    command += ` --topic-threshold ${topicThreshold}`;
  }
  if (maxTopics !== 5) {
    command += ` --max-topics ${maxTopics}`;
  }
  if (maxBullets !== 5) {
    command += ` --max-bullets ${maxBullets}`;
  }
  if (debug) {
    command += ` --debug`;
  }
  
  return command;
}
```

### 字元跳脫處理（Agent B）

Frontend 產生指令時需處理特殊字元：

```typescript
function escapeShellArg(text: string): string {
  // Windows PowerShell 跳脫規則
  return text
    .replace(/\\/g, '\\\\')  // 反斜線
    .replace(/"/g, '\\"')     // 雙引號
    .replace(/\n/g, '\\n')    // 換行
    .replace(/\r/g, '\\r');   // 回車
}
```

### 路徑處理

- Backend 輸出：`../frontend/public/deck.json`（相對於 `backend/` 目錄）
- Frontend 讀取：`/deck.json`（相對於 web root，即 `public/`）
- 絕對路徑：`<專案根目錄>/frontend/public/deck.json`

### 相容性

- **作業系統**：Windows 10+（主要開發環境）
- **瀏覽器**：Chrome/Edge 桌面版
- **Python**：3.11+
- **Node.js**：18+

## 限制與範圍外

### 範圍內
- ✅ Markdown 和純文字檔案（`.md`, `.txt`）
- ✅ 簡易 Demo 版整合（手動執行指令）
- ✅ 本地開發與測試
- ✅ 固定 JSON schema（版本 1.0）

### 範圍外
- ❌ PDF、DOCX、HTML 等其他檔案格式
- ❌ URL 輸入與網頁抓取
- ❌ HTTP API server（Backend 只提供 CLI）
- ❌ 即時雙向通訊（WebSocket、SSE 等）
- ❌ 帳號、權限、多人協作功能
- ❌ 雲端部署（目前僅本地執行）
- ❌ 精緻動畫與複雜 UI
- ❌ 成本最佳化策略
- ❌ 自動化 GitHub 操作（C-agent）
