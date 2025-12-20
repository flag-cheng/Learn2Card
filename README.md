# Learn2Cards · 文件歸納切卡機（P0 UI Shell）

Learn2Cards 是一個以 **React + TypeScript + Vite** 打造的「文件歸納切卡機」前端外殼。  
目前專案已整合一個 **單一介面流程**：使用者在前端直接**上傳 Markdown/純文字**，後端即時分析並回傳 deck JSON，前端立刻渲染成可翻閱的卡片。

同時仍保留 demo 用的 `deck.json` / `deck.sample.json`（位於 `frontend/public/`），可在不啟動後端時用預設載入方式展示 UI。

## 📂 目錄結構

- `frontend/`：Vite + React 前端（UI shell、sampleDeck、相關設定）。
- `backend/`：Agent A 核心邏輯（產生/驗證 deck）+ API（提供 UI 上傳即時產生卡片）。
- `docs/`：需求與設計文件（PRDs，spec）。


## 🔍 功能摘要（P0）

P0 版本的 UI shell 提供：

- ⬆️ **上傳檔案並即時產生卡片**
  - 上傳 `.md/.txt` → 呼叫 `POST /api/generate` → 立刻顯示卡片
  - 仍可從 `/deck.json` 或 `/deck.sample.json` 載入（無後端也能 demo）

- 📊 **左側統計資訊**（schema `1.0.0`）
  - 段落數 `stats.totalParagraphs`
  - 重點數 `stats.totalKeypoints`
  - 主題數 `stats.totalTopics`
  - 卡片數 `stats.totalCards`

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

- Node.js **18+**
- 套件管理工具可使用 `npm` 或 `pnpm`（此專案預設使用 npm scripts）


## 🧪 安裝與開發（Development）

### 只看 UI（不啟動後端）

在專案根目錄執行（前端位於 `frontend/`）：

```bash
cd frontend
npm install
npm run dev    # 啟動開發伺服器（預設 http://localhost:5173）
```

啟動後：

- 開啟瀏覽器造訪 http://localhost:5173
- 預設會嘗試載入 `/deck.json`，失敗則載入 `/deck.sample.json`

### 上傳檔案即時產生卡片（建議）

先啟動後端：

```bash
python3 -m pip install -U fastapi "uvicorn[standard]" python-multipart
python3 -m uvicorn backend.main:app --reload --port 8000
```

再啟動前端（已設定 `/api` 代理到 `http://localhost:8000`）：

```bash
cd frontend
npm run dev
```

最後在 UI 的「上傳檔案（Markdown/純文字）」選擇檔案，即可立即看到卡片生成結果。


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


## deck.json 產生與驗證（Agent A）

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

可在 repo 根目錄執行：

```bash
./cli generate --input docs/prd/agent-a.md --force
./cli validate --input frontend/public/deck.json
```


## 開發備註
- 尚未實作 RWD、loading、錯誤提示等進階狀態。
- 目前所有卡片資料來源皆為前端內建 `sampleDeck`。
- UI 微調建議直接修改 `src/App.css` ，結構調整則從 `src/App.tsx` 著手。


## 授權
僅供內部示範/開發使用。

