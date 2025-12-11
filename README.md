# Learn2Cards · 文件歸納切卡機（P0 UI Shell）

Learn2Cards 是一個以 **React + TypeScript + Vite** 打造的「文件歸納切卡機」前端外殼。  
目前專案處於 **P0 階段**：只示範 UI 與基本互動，**所有資料來自內建 `sampleDeck` 假資料**，不需後端或 LLM。

未來階段會由 Agent 產生 `deck.json`，再接入這個 UI 進行展示。

## 📂 目錄結構

- `frontend/`：Vite + React 前端（UI shell、sampleDeck、相關設定）。
- `backend/`：預留給 Cloud Agent / API / 推論邏輯，目前僅放佔位檔。
- `docs/`：需求與設計文件。


## 🔍 功能摘要（P0）

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

- Node.js **18+**
- 套件管理工具可使用 `npm` 或 `pnpm`（此專案預設使用 npm scripts）


## 🧪 安裝與開發（Development）

在專案根目錄執行（前端位於 `frontend/`）：

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
- 所有顯示內容皆來自內建 sampleDeck，此階段不需任何網路連線或後端服務


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


## 假資料與未來 deck.json 接入說明

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


## 開發備註
- 尚未實作 RWD、loading、錯誤提示等進階狀態。
- 目前所有卡片資料來源皆為前端內建 `sampleDeck`。
- UI 微調建議直接修改 `src/App.css` ，結構調整則從 `src/App.tsx` 著手。


## 授權
僅供內部示範/開發使用。

