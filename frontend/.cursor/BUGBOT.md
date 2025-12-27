# BUGBOT Frontend 審查規範

> 本檔案定義 `frontend/` 目錄專屬規則，會與全域規則（`.cursor/BUGBOT.md`）疊加使用。

---

## 🔴 嚴重問題（禁止合併）

### 套件管理器限制 [tooling]
**強制使用 `npm`**，禁止任何其他套件管理器。

```bash
# ❌ 絕對禁止
yarn add react-router-dom
pnpm install
bun add axios
npm create vite@latest      # 重建專案
rm -rf src/App.tsx          # 刪除現有程式碼

# ✅ 唯一正確做法
cd frontend
npm install                 # 安裝依賴
npm install axios           # 新增套件
npm install -D vitest       # 新增開發依賴
npm run dev                 # 開發模式
npm run build               # 建置
```

**原因**：專案使用 npm + package-lock.json 鎖定依賴版本，更換套件管理器會導致版本不一致。

**檢查方式**：
- 不得存在 `yarn.lock`、`pnpm-lock.yaml`、`bun.lockb`
- 只能修改 `package.json` 和 `package-lock.json`

---

## 🟡 重要問題（強烈建議修正）

### 元件 Props 型別定義 [quality]
**所有元件必須定義 Props 介面**。

```typescript
// ❌ 錯誤：沒有型別定義
function Card({ title, bullets, onNext }) {
  return <div>...</div>;
}

// ✅ 正確：明確定義介面
interface CardProps {
  title: string;
  bullets: string[];
  onNext: () => void;
  isLast?: boolean;  // optional props 用 ?
}

function Card({ title, bullets, onNext, isLast = false }: CardProps) {
  return <div>...</div>;
}
```

**要求**：
- 使用 `interface` 定義 Props（物件結構）
- 使用 `type` 定義聯集型別（`type Status = 'idle' | 'loading' | 'error'`）
- Optional props 用 `?` 標記，並提供預設值

---

## 🟢 建議改善（程式碼品質）

### CSS 命名規範 [style]
```css
/* ✅ 正確：kebab-case 命名 */
.card-viewer { }
.status-banner { }
.primary-button { }

/* ❌ 錯誤：camelCase 或 PascalCase */
.cardViewer { }
.StatusBanner { }

/* ❌ 錯誤：過度使用 !important */
.button {
  color: red !important;  /* 只在覆蓋第三方樣式時使用 */
}
```
---

## 🚫 專案禁止事項總結

以下行為**絕對禁止**，發現立即拒絕合併：

### 🔴 嚴重（會導致系統錯誤）
- ❌ 使用 yarn、pnpm、bun 等其他套件管理器

### 🟡 重要（違反專案規範）
- ⚠️ 元件缺少 Props 型別定義

### 🟢 建議改善）
- 💡 CSS 類別使用 camelCase（建議用 kebab-case）

