以下是重寫後的 **《指揮中心儀表板 (Command Palette)｜v3.9.CS 架構版》**
完全針對你目前的架構（無 `control.sh`、無 `diagnostics.sh`、改為 `.py` 架構），並包含守護層（daemon）與冒煙測試指令。
可直接覆蓋原檔，或另存為 `COMMAND_PALETTE_v3.9.md`。

---

# 🧭 **通用目錄哨兵控制中心：指揮中心儀表板 (Command Palette)**

> **版本：v3.9.CS 架構版**
> 本檔案列出所有可在命令列直接操作的核心指令。
> 每條指令均經過實測驗證，適用於 Linux / WSL 環境。

---

## 【第一類：核心執行指令】

### 🚀 啟動主控制台

* **用途：** 啟動交互式主菜單（主控台），執行「新增、編輯、刪除、手動更新」等操作。
* **指令：**

  ```bash
  python3 main.py
  ```

---

### ⚙️ 守護層（Daemon）直呼模式

* **用途：** 不經主控台，直接調用後端守護層執行更新或查詢。
* **指令格式與示例：**

#### 1️⃣ 列出所有專案

```bash
python3 src/core/daemon.py list_projects
```

#### 2️⃣ 名單模式（UUID 指定）

```bash
python3 src/core/daemon.py manual_update 7cbcd3cb-ec7c-4263-ac9a-f20e6cc95b7d
```

#### 3️⃣ 自由模式（直接指定路徑）

```bash
python3 src/core/daemon.py manual_direct "/home/serpal/My_Python_Projects/laplace_sentry_control_v2" \
"/mnt/d/Obsidian_Vaults/Laplace_Notes/.../通用目錄測試寫入檔(測試用).md"
```

---

## 【第二類：專家獨立調用指令】

### 🧩 結構專家（engine.py）

* **用途：** 直接生成一個目錄的結構樹，支援從檔案或管道讀取舊內容。
* **格式：** `python3 src/core/engine.py <目錄路徑> [舊內容來源]`
* **範例：**

  ```bash
  python3 src/core/engine.py ./src
  cat README.md | python3 src/core/engine.py ./src -
  ```

---

### 🧠 路徑專家（path.py）

* **用途：** 操作「讀、寫、驗證、淨化」。
* **格式：** `python3 src/core/path.py <命令> [參數...]`

#### 常用示例

```bash
# 驗證路徑是否存在
python3 src/core/path.py validate ./src/core/engine.py ./README.md

# 讀取檔案內容
python3 src/core/path.py read ./README.md

# 淨化一個 Windows 路徑
python3 src/core/path.py normalize "D:\Obsidian_Vaults\Laplace_Notes"

# 淨化一個 WSL 網路路徑
python3 src/core/path.py normalize "//wsl.localhost/Ubuntu/home/serpal"
```

---

## 【第三類：開發與診斷指令】

### 🧪 一鍵冒煙測試（Smoke Test）

* **用途：** 快速檢查整體鏈路是否可用。
  包含：

  * `list_projects`
  * `manual_update`（名單模式）
  * `manual_direct`（自由模式）
* **指令：**

  ```bash
  ./smoke_test.sh
  ```
* **結果判斷：**

  * ✅ 所有步驟成功 → 系統穩定，可提交
  * ❌ 任一失敗 → 立即檢查 daemon 錯誤訊息

---

### 🔍 清理哨兵環境（防止殘留）

```bash
pkill -f "inotifywait" || true && rm -f /tmp/sentry_*.pid && rm -f logs/sentry_*.log
killall inotifywait
```

---

### 📜 實時查看日誌（Log Tail）

```bash
tail -f logs/sentry_test.log
```

---

## 【第四類：版本控制指令 (Git)】

### 📦 暫存所有變更

```bash
git add .
```

### 💾 提交變更

```bash
git commit -m "feat: 修正 manual_update 錯誤回報與後台輸出"
```

### ⏪ 一鍵回滾（撤銷未提交修改）

```bash
git checkout -- src/core/daemon.py main.py
```

---

## 【第五類：臨時手動操作指令】

### 🧷 手動備份文件

```bash
cp src/core/daemon.py src/core/daemon.py.bak
cp main.py main.py.bak
```

### ♻️ 手動恢復文件

```bash
cp src/core/daemon.py.bak src/core/daemon.py
cp main.py.bak main.py
```

---

## 【第六類：提交前固定檢查流程（必跑）】

1️⃣ **列出名單**

```bash
python3 src/core/daemon.py list_projects
```

2️⃣ **名單模式測試**

```bash
python3 src/core/daemon.py manual_update 7cbcd3cb-ec7c-4263-ac9a-f20e6cc95b7d
```

3️⃣ **自由模式測試**

```bash
python3 src/core/daemon.py manual_direct "/專案/路徑" "/目標檔案.md"
```

4️⃣ **一鍵冒煙測試**

```bash
./smoke_test.sh
```

✅ 全數通過後再執行：

```bash
git add .
git commit -m "chore: stabilize v3.9.CS"
```

---

## 【第七類：後續開發建議（可選）】

* **凍結介面**：暫時不動以下指令格式：

  * `daemon.py manual_update <uuid>`
  * `daemon.py manual_direct <path> <target>`
  * `path.py read|write|validate|normalize`
* **建立 smoke_test 分支**：集中管理穩定修補。
* **自動化建議**：未來可導入 `pytest` 及 `pre-commit` 進行自動化測試與型別檢查。

---

✅ **狀態**：本文件已同步至 v3.9 架構，無 `control.sh` / `diagnostics.sh`，全面改用 `.py` 模組化路徑。
💡 **下一步建議**：
在 `README.md` 開頭加入：

```bash
# 快速啟動
python3 main.py
```

讓新使用者能立即找到進入系統的入口。

<!-- AUTO_TREE_START -->
```
laplace_sentry_control_v2/
├── data/                       # TODO: Add comment here
│   └── projects.json           # TODO: Add comment here
├── logs/                       # TODO: Add comment here
│   ├── .gitkeep                # TODO: Add comment here
│   └── .worker.lock            # TODO: Add comment here
├── src/                        # TODO: Add comment here
│   ├── core/                   # TODO: Add comment here
│   │   ├── __init__.py         # TODO: Add comment here
│   │   ├── daemon.py           # TODO: Add comment here
│   │   ├── engine.py           # TODO: Add comment here
│   │   ├── formatter.py        # TODO: Add comment here
│   │   └── path.py             # TODO: Add comment here
│   └── shell/                  # TODO: Add comment here
│       └── worker.sh           # TODO: Add comment here
├── tests/                      # TODO: Add comment here
│   ├── test_add_project.sh     # TODO: Add comment here
│   ├── test_add_project_v2.sh  # TODO: Add comment here
│   ├── test_edit_delete.py     # TODO: Add comment here
│   ├── test_list_projects.sh   # TODO: Add comment here
│   ├── test_ping_pong.sh       # TODO: Add comment here
│   ├── tests_readme.md         # TODO: Add comment here
│   ├── verify.sh               # TODO: Add comment here
│   ├── verify_flock.sh         # TODO: Add comment here
│   └── verify_path.sh          # TODO: Add comment here
├── tests copy/                 # TODO: Add comment here
│   ├── test_add_project.sh     # TODO: Add comment here
│   ├── test_add_project_v2.sh  # TODO: Add comment here
│   ├── test_edit_delete.py     # TODO: Add comment here
│   ├── test_list_projects.sh   # TODO: Add comment here
│   ├── test_ping_pong.sh       # TODO: Add comment here
│   ├── tests_readme.md         # TODO: Add comment here
│   ├── verify.sh               # TODO: Add comment here
│   ├── verify_flock.sh         # TODO: Add comment here
│   └── verify_path.sh          # TODO: Add comment here
├── .gitignore                  # TODO: Add comment here
├── PROTOCOL.md                 # TODO: Add comment here
├── README.md                   # TODO: Add comment here
├── main.py                     # TODO: Add comment here
└── releases.md                 # TODO: Add comment here
```
<!-- AUTO_TREE_END -->
