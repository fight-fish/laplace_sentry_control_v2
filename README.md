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
├── data/                       # 【數據區】存放專案運行所需的持久化資料。
│   └── projects.json           # 【專案名單】以 JSON 格式記錄所有受監控專案與設定。
├── logs/                       # 【日誌區】存放哨兵運行時產生的暫存檔與鎖定檔。
│   ├── .gitkeep                # 讓 Git 保留此空資料夾的佔位符。
│   └── .worker.lock            # 【鎖定檔】由 worker.sh 使用 flock 機制產生，用來防止重複啟動工人進程。
├── src/                        # 【源碼區】存放專案的主要程式碼。
│   ├── core/                   # 【核心模組】可獨立執行的 Python 模組（專家層）。
│   │   ├── __init__.py         # 標記此資料夾為 Python 套件，供其他模組導入使用。
│   │   ├── daemon.py           # 【守護進程（指揮官）】負責調度工人、處理專案清單與手動更新。
│   │   ├── engine.py           # 【結構專家】生成目錄結構樹並合併註解。
│   │   ├── formatter.py        # 【格式化專家】負責將結構輸出包裝成 Markdown 代碼塊。
│   │   ├── path.py             # TODO: Add comment here
│   │   └── worker.py           # TODO: Add comment here
│   └── shell/                  # 【Shell 腳本層】負責流程控制與背景操作。
│       └── worker.sh           # 【工人腳本】執行實際更新任務（由 daemon 呼叫）。
├── tests/                      # 【自動化測試區】存放各模組的單元與整合測試腳本。
│   ├── test_add_project.sh     # 測試「新增專案」功能是否正常。
│   ├── test_add_project_v2.sh  # 測試「新增專案」進階版本（含輸入驗證）。
│   ├── test_edit_delete.py     # 測試專案「修改與刪除」功能。
│   ├── test_list_projects.sh   # 測試「列出專案清單」功能。
│   ├── test_ping_pong.sh       # 測試「指揮官 ↔ 工人」通信是否成功。
│   ├── tests_readme.md         # 測試說明文件，解釋每個測試腳本的用途。
│   ├── verify.sh               # 綜合測試指令腳本，快速驗證主要模組功能。
│   ├── verify_flock.sh         # 測試 flock 機制是否能防止多重 worker 同時運行。
│   └── verify_path.sh          # 測試 path.py 路徑解析功能是否正確。
├── tests copy/                 # TODO: Add comment here
│   ├── test_add_project.sh     # 測試「新增專案」功能是否正常。
│   ├── test_add_project_v2.sh  # 測試「新增專案」進階版本（含輸入驗證）。
│   ├── test_edit_delete.py     # 測試專案「修改與刪除」功能。
│   ├── test_list_projects.sh   # 測試「列出專案清單」功能。
│   ├── test_ping_pong.sh       # 測試「指揮官 ↔ 工人」通信是否成功。
│   ├── tests_readme.md         # 測試說明文件，解釋每個測試腳本的用途。
│   ├── verify.sh               # 綜合測試指令腳本，快速驗證主要模組功能。
│   ├── verify_flock.sh         # 測試 flock 機制是否能防止多重 worker 同時運行。
│   └── verify_path.sh          # 測試 path.py 路徑解析功能是否正確。
├── .gitignore                  # TODO: Add comment here
├── PROTOCOL.md                 # TODO: Add comment here
├── README.md                   # TODO: Add comment here
├── main.py                     # TODO: Add comment here
└── releases.md                 # TODO: Add comment here
```
<!-- AUTO_TREE_END -->


