# BUGBOT Backend 審查規範

> 本檔案定義 `backend/` 目錄專屬規則，會與全域規則（`.cursor/BUGBOT.md`）疊加使用。

---

## 🔴 嚴重問題（禁止合併）

### 套件管理器限制 [tooling]
**強制使用 `uv`**，禁止任何其他套件管理器。

```bash
# ❌ 絕對禁止
pip install fastapi
pip install -r requirements.txt
poetry add fastapi
conda install python
python -m venv .venv
source .venv/bin/activate

# ✅ 唯一正確做法
cd backend
uv sync                    # 同步依賴
uv add fastapi            # 新增套件
uv add --dev pytest       # 新增開發依賴
uv run python script.py   # 執行程式
```

**原因**：專案統一使用 uv 管理依賴，確保環境一致性。uv 會自動管理虛擬環境，無需手動操作。

**檢查方式**：
- 檢查 Git diff 是否有 `requirements.txt`（應不存在）
- 檢查 commit 是否包含 `.venv/`（應在 .gitignore）

### 依賴管理檔案 [tooling]
```bash
# ✅ 正確：唯一允許的依賴檔案
pyproject.toml    # 專案設定與依賴定義
uv.lock           # 鎖定版本（自動生成）

# ❌ 禁止：不得存在以下檔案
requirements.txt
requirements-dev.txt
Pipfile
poetry.lock
environment.yml
```
---

## 🟡 重要問題（強烈建議修正）

### 型別標註 [quality]
**所有公開函式建議有完整型別標註**

```python
# ⚠️ 不適合：缺少型別標註
def process_text(text):
    return text.strip()

# ⚠️ 不適合：不完整的標註
def process_text(text: str):  # 缺少回傳型別
    return text.strip()

# ✅ 推薦：完整標註
def process_text(text: str) -> str:
    return text.strip()

# ✅ 推薦：使用 typing 模組處理複雜型別
from typing import Optional, Literal

def build_deck(
    *,
    text: str,
    max_topics: int = 5,
) -> dict[str, Any]:
    ...
```

**原因**：型別標註可在開發階段發現 80% 的錯誤，顯著提升程式碼品質。

---

## 🟢 建議改善（程式碼品質）

### API 錯誤格式（建議統一）[api]
**所有錯誤回應建議遵循此格式**，確保前端可預期處理。

**HTTP 狀態碼語義**（建議遵守）：
- `200`：成功
- `400`：客戶端錯誤（參數錯誤、驗證失敗）
- `500`：伺服器內部錯誤（程式 bug、依賴失敗）
- 不使用 `422`：FastAPI 預設的驗證錯誤應轉為 `400`

```python
# ✅ 正確：區分錯誤類型
from fastapi import HTTPException

try:
    result = build_deck(text=req.text, ...)
except ProcessingError as e:        # 使用者輸入問題
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:                # 程式內部問題
    raise HTTPException(status_code=500, detail=f"內部錯誤：{e}")
```

**原因**：統一格式讓前端可以用單一邏輯處理所有錯誤，改善使用者體驗。

---

## 🚫 專案禁止事項總結
以下行為**絕對禁止**，發現立即拒絕合併：

### 🔴 嚴重（會導致系統錯誤）
- ❌ 使用 pip、poetry、conda 等其他套件管理器
- ❌ 手動建立 `.venv` 或使用 `requirements.txt`

### 🟡 重要（違反專案規範）
- ⚠️ 缺少型別標註或使用 `# type: ignore`

### 🟢 建議改善）
- 💡 API 錯誤訊息用英文或格式不統一




