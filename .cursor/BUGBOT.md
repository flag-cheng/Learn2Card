# BUGBOT 全域審查規範

> 本檔案定義專案通用規則，適用於所有程式碼。  
> 特定模組規則請參考：`backend/.cursor/BUGBOT.md`、`frontend/.cursor/BUGBOT.md`

---

## 🔴 嚴重問題（必須修正，否則不得合併）

### 空的錯誤處理 [quality]
```python
# ❌ 禁止：空的 except 區塊
try:
    risky_operation()
except:
    pass

# ✅ 正確：記錄錯誤或提供降級方案
try:
    risky_operation()
except ValueError as e:
    logger.error(f"處理失敗：{e}")
    return default_value
```
**原因**：靜默失敗會隱藏問題，難以除錯。

---

## 🟡 重要問題（強烈建議修正）

### 語言規範 [i18n]
**必須使用繁體中文**用於：
- 使用者可見的錯誤訊息
- 註解說明（解釋為什麼這樣寫）
- commit message 的描述部分
- 文件（README、API 文件）

**可使用英文**用於：
- 變數名稱、函式名稱（遵循各語言慣例）
- 技術術語（React、API、TypeScript）

```python
# ❌ 錯誤
raise ValueError("Invalid input")  # 使用者會看到

# ✅ 正確
raise ValueError("輸入格式錯誤：請提供有效的電子郵件地址")
```
---

## 🟢 建議改善

### Git Commit Message 格式 [git]
**格式**：`英文類別：繁體中文描述`

**允許的類別**：`add`、`fix`、`restruct`、`test`、`doc`（僅此五種）

**描述要求**：
- 長度：10～30 字
- 內容：說明「改了什麼」，不是「想做什麼」
- 禁用詞：`try`、`change`、`update`（太空泛）

```bash
# ✅ 正確範例
add：支援 Markdown 條列解析為卡片
fix：分頁超出範圍時回傳空清單並提示
restruct：將分頁邏輯抽成 paginator 模組
test：補齊混中英與空文件案例
doc：更新 API 錯誤碼說明

# ❌ 錯誤範例
update：改一些東西           # 太空泛
fix：try something          # 英文描述 + 空泛
add: 新增功能                # 冒號後沒空格
新增：支援卡片               # 類別用中文
```

---

## 📊 問題標籤說明

- `[security]`：安全性問題，最高優先級
- `[quality]`：程式碼品質問題
- `[tooling]`：工具鏈與環境設定（如套件管理器、建置工具）
- `[api]`：API 設計與規範（錯誤格式、狀態碼、回應結構）
- `[i18n]`：國際化/語言相關
- `[git]`：版本控制規範
- `[style]`：程式碼風格與命名規範


