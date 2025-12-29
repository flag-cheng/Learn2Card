# Learn2Cards · 文件歸納切卡機

Learn2Cards 是一個將 **Markdown/純文字文件** 自動歸納整理成「翻卡式大綱」的工具。  
專案採用 **前後端分離架構**，由 **Cloud Agent 協作開發**，展示 AI Agent 驅動的軟體開發流程。

## 📝 Testing Bugbot [i18n] Rule Violation

**Note**: This section is intentionally written in English to test if Bugbot detects violations of the [i18n] rule which requires Traditional Chinese for all documentation. This is a deliberate test case to validate the BUGBOT.md configuration.

**Purpose**: According to `.cursor/BUGBOT.md`, all documentation including README files must be written in Traditional Chinese. This English paragraph violates that rule and should trigger a Bugbot warning if the rule is properly enforced.

**Expected Behavior**: If Bugbot correctly implements the [i18n] rule checking, it should report this section as a violation because:
- This is documentation (README file)
- The content is in English instead of Traditional Chinese
- The BUGBOT.md explicitly lists "文件（README、API 文件）" as requiring Traditional Chinese

## 🎯 專案目標

輸入 Markdown 或純文字 → 自動切段 → 提取重點與關鍵詞 → 語意分群 → 生成卡片 → 提供翻卡式 UI 瀏覽

**技術架構**：
- **Frontend (Agent B)**：React 18 + TypeScript + Vite 5，提供檔案上傳與卡片瀏覽介面
- **Backend (Agent A)**：Python 3.11+ + uv，處理 NLP/LLM 管線與卡片生成邏輯

**開發模式**：
- Agent A 和 Agent B 由 **Cloud Agent** 在獨立分支上平行開發
- 最後由整合任務（global.md）merge 分支並驗證完整流程

## 📂 目錄結構

```
Learn2Cards-2/
├── frontend/              # Agent B：React + TypeScript 前端
│   ├── src/
│   │   ├── App.tsx       # 主要 UI 與互動邏輯
│   │   ├── types.ts      # 型別定義
│   │   └── sampleDeck.ts # P0 假資料
│   ├── package.json      # npm 依賴管理
│   └── vite.config.ts    # Vite 設定
│
├── backend/              # Agent A：Python 核心邏輯
│   ├── main.py          # 主程式（由 Cloud Agent 實作）
│   └── pyproject.toml   # uv 依賴管理
│
├── docs/                 # 專案文件
│   ├── prd/
│   │   ├── agent-a.md   # Agent A PRD（後端 NLP/LLM 管線）
│   │   ├── agent-b.md   # Agent B PRD（前端 UI 介面）
│   │   ├── global.md    # 整合 PRD（merge 與流程驗證）
│   │   └── p0-ui-shell.md # P0 階段需求
│   └── spec/
│       └── technical-spec.md # 技術規格
│
└── .cursor/
    └── rules/            # 開發規則（自動套用）
        ├── backend-rule.mdc   # Backend 技術棧與規範
        └── frontend-rule.mdc  # Frontend 技術棧與規範
```


## 🗺️ 專案里程碑

- **M1 (P0)** ✅：UI Shell + 假資料 + JSON schema + PRD 文件齊備
- **M2**：Agent A 完成後端 NLP/LLM 管線（由 Cloud Agent 在獨立分支實作）
- **M3**：Agent B 完成前端檔案上傳與整合（由 Cloud Agent 在獨立分支實作）
- **M4**：整合 Agent A/B 分支，驗證「上傳 → 分析 → 出卡」完整流程
- **M5**：整合分支驗收通過後，merge 到 master

## 🔍 功能摘要（P0 - 當前階段）

P0 版本的 UI shell 提供：

- 📊 **左側統計資訊**
  - 段落數（`paragraphCount`）
  - 主題數（`topicCount`）
  - 卡片數（`cardCount`）

- 🗂️ **左側主題列表**
  - 一個「全部主題」按鈕
  - 多個主題按鈕（每個代表一個 topic）
  - 點擊主題按鈕 → 切換右側可見卡片的集合，並從該集合第 1 張開始顯示

- 🧾 **右側卡片檢視**
  - 顯示：目前卡片所屬主題標籤（`topic.title`，無則顯示「未命名主題」）
  - 顯示：卡片標題（`card.title`，無則顯示「未命名卡片」）
  - 顯示：內容 bullets（1–5 行），無 bullets 時顯示「（此卡片目前沒有內容）」  
  - 下方提供「上一張 ← / 下一張 →」按鈕翻閱卡片
  - 當可見卡片集合為空時，顯示空狀態文字：
    - `目前沒有卡片可顯示（可能是資料尚未產生）。`


## 📁 專案結構（與 P0 相關的重點檔案）

- `frontend/src/App.tsx`  
  主要 UI 結構與互動邏輯（主題切換、翻卡、index 計算等）。

- `frontend/src/App.css`  
  P0 的主要樣式與版面配置。

- `frontend/src/sampleDeck.ts`  
  P0 階段使用的內建假資料 `sampleDeck`，實作 `Deck` 的最小示範內容。

- `frontend/src/types.ts`  
  型別定義，包括：
  - `Paragraph`
  - `Topic`
  - `Card`
  - `DeckStats`
  - `Deck`

- `docs/prd/p0-ui-shell.md`  
  P0 需求與行為說明（畫面分區、互動邏輯、狀態變化等）。


## ⚙️ 環境需求

### Frontend (Agent B)
- **Node.js 18+**
- **套件管理器**：npm（不使用 yarn/pnpm）
- **技術棧**：React 18 + TypeScript + Vite 5
- 詳細規範請參考：`.cursor/rules/frontend-rule.mdc`

### Backend (Agent A)
- **Python 3.11+**
- **套件管理器**：uv（不使用 pip/poetry/conda）
- **依賴管理**：pyproject.toml
- 詳細規範請參考：`.cursor/rules/backend-rule.mdc`


## 🧪 安裝與開發（Development）

### Frontend 開發（P0 當前可用）

在專案根目錄執行：

```bash
cd frontend
npm install
npm run dev    # 啟動開發伺服器（預設 http://localhost:5173）
```

啟動後：

- 開啟瀏覽器造訪 http://localhost:5173
- 左側可看到統計資訊與主題列表
- 點選主題按鈕會切換右側可見卡片集合，並重置到該集合的第 1 張
- 右側卡片可透過「上一張 / 下一張」按鈕翻閱
- **P0 階段**：所有顯示內容皆來自內建 sampleDeck，不需任何網路連線或後端服務

### Backend 開發（M2 階段，由 Cloud Agent 實作）

安裝依賴：

```bash
cd backend
uv sync          # 根據 pyproject.toml 安裝依賴
```

執行程式：

```bash
uv run python main.py        # 執行主程式
uv run python -m pytest      # 執行測試
```

**重要**：
- 使用 `uv run` 執行所有 Python 指令，不需手動啟動虛擬環境
- uv 會自動管理虛擬環境
- 新增依賴使用 `uv add package_name`


## 📦 Build：產出靜態網站

在 `frontend/` 目錄下執行：

```bash
cd frontend
npm run build  # 產出靜態檔案
```

Vite 會將前端打包為純靜態網站，輸出到 `frontend/dist/`：
- `frontend/dist/index.html` — 單頁應用入口頁面
- `frontend/dist/assets/*.js` — React + TypeScript 編譯/壓縮後的 JavaScript
- `frontend/dist/assets/*.css` — 打包後的樣式檔

Build 完成後，`frontend/dist/` 內容就是可直接部署的前端網站。
只要有 HTTP 靜態服務（如 GitHub Pages、Netlify、S3、Nginx），瀏覽器即可直接使用，不需再啟動 Node.js 或額外後端程式。

你可以用：
```bash
cd frontend
npm run preview
```
在本機啟動簡易預覽伺服器，測試打包後的版本。


## 🤖 Agent 角色與分工

### Agent A：核心 NLP/LLM 管線（Backend）
**負責**：文件 → 段落 → 重點/關鍵詞 → 語意分群 → 卡片草稿 → JSON 輸出

**技術棧**：Python 3.11+ + uv + LLM API + embedding 模型

**輸入限制**：
- 僅接受**純文字字串**作為輸入
- 不處理檔案讀取、URL 抓取或任何 I/O 操作

**輸出**：符合固定 schema 的 deck.json

**PRD**：`docs/prd/agent-a.md`

### Agent B：Web 翻卡介面（Frontend）
**負責**：檔案上傳 → 呼叫 Agent A → 顯示卡片 → 翻卡/統計/主題切換

**技術棧**：React 18 + TypeScript + Vite 5 + npm

**輸入限制**：
- **僅支援** `.txt` 和 `.md` 檔案上傳
- 或提供文字框讓使用者直接貼上純文字
- **不支援 URL 輸入**、網頁抓取或其他格式（如 PDF、DOCX）

**功能**：
- 檔案上傳與格式驗證
- 呼叫 Agent A 的 API 進行分析
- 即時顯示生成的卡片
- 翻卡、主題切換、統計展示

**PRD**：`docs/prd/agent-b.md`

### 整合任務（global.md）
**負責**：
- Merge Agent A 和 Agent B 的開發分支到新的整合分支
- 驗證「上傳 → 後端分析 → 即時出卡」完整流程
- 處理整合問題（CORS、API 格式、錯誤處理等）
- 驗收通過後再 merge 到 master

**PRD**：`docs/prd/global.md`

## 📋 假資料與未來 deck.json 接入說明

**P0 假資料**：sampleDeck

目前 P0 使用的資料來源是內建的 sampleDeck 物件，其結構對應 Deck 型別：

- sampleDeck.stats
  - paragraphCount — 段落數量
  - topicCount — 主題數量
  - cardCount — 卡片數量

- sampleDeck.topics
  - 每個主題包含 id 與 title，以及與段落的關聯（未來可延伸）

- sampleDeck.cards
  - 每張卡片包含：
    - id
    - topicId（對應 topics.id）
    - title
    - bullets[]（1–5 筆文字）

### 未來接入 deck.json（P1 / P2 預留）

後續階段會由 A-agent 產生標準格式的 deck.json。
接入方式預期如下：

1.將產生好的 deck.json 放入專案的 `frontend/public/` 目錄：
```bash
frontend/public/deck.json
```

2.Vite build 時會自動將 `frontend/public/deck.json` 複製到 `frontend/dist/deck.json`

3.UI 將改為使用 fetch('/deck.json') 載入 deck 資料，例如：

```bash
fetch("/deck.json")
  .then((res) => res.json())
  .then((data) => setDeck(data));
```
如此一來，可以先用工具將文件整理成 deck.json，再 build 出一套「UI + 資料」的靜態網站，丟到任一靜態空間即可直接翻卡瀏覽。


## 🔄 Cloud Agent 協作流程

本專案採用 **Cloud Agent 驅動開發**，展示 AI Agent 如何協作完成複雜專案：

### 開發流程
1. **準備階段（M1）** ✅
   - 撰寫詳細的 PRD（agent-a.md、agent-b.md、global.md）
   - 建立技術規則（.cursor/rules/backend-rule.mdc、frontend-rule.mdc）
   - 準備 P0 UI Shell 與假資料

2. **平行開發（M2 + M3）**
   - 使用 Web 版 Cloud Agent，提供對應的 PRD
   - Agent A：在獨立分支實作後端 NLP/LLM 管線
   - Agent B：在獨立分支實作前端檔案上傳與整合
   - 兩個 Agent 同時開工，互不等待

3. **整合驗證（M4）**
   - 根據 global.md，merge A/B 分支到新的整合分支
   - 在整合分支上驗證完整流程
   - 處理可能的整合問題

4. **發布（M5）**
   - 整合分支驗收通過後，merge 到 master

### PRD 撰寫重點
為確保 Cloud Agent 準確執行，PRD 採用以下結構：
- **技術棧與環境**：明確指定工具、版本、安裝指令（參考 .cursor/rules/）
- **實作指引與限制**：
  - **必須遵守**：強制性要求
  - **不得實作** ❌：明確禁止的項目（防止 Agent 自由發揮）
- **驗收標準**：具體的可測試條件

### 技術規則檔案
- `.cursor/rules/backend-rule.mdc`：Backend 開發規範（Python + uv）
- `.cursor/rules/frontend-rule.mdc`：Frontend 開發規範（React + npm）
- 這些規則會自動套用，確保 Cloud Agent 遵守專案規範

## 開發備註
- **P0 階段**：尚未實作 RWD、loading、錯誤提示等進階狀態
- 目前所有卡片資料來源皆為前端內建 `sampleDeck`
- UI 微調建議直接修改 `src/App.css`，結構調整則從 `src/App.tsx` 著手
- **技術限制**：
  - Backend 只能使用 uv，不得使用 pip/poetry
  - Frontend 只能使用 npm，不得改用 yarn/pnpm
  - Frontend 必須在現有專案基礎上擴充，不得重建
  - 輸入只支援 .txt/.md 檔案，不支援 URL 或 PDF


## 授權
僅供內部示範/開發使用。

