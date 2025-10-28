```markdown

### **指揮中心儀表板 (Command Palette)**

此處將記錄本專案所有相關的操作指令，以便隨時複製查閱。

### 【第一類：核心執行指令】

*日常使用我們專案的核心功能。*

---

#### 運行主控制台
- **用途：** 啟動交互式主菜單，這是與本系統互動的主要入口。
- **指令：**
  ```bash
  ./src/shell/control.sh
  ```

#### 運行一鍵安裝器
- **用途：** 在新環境下，自動完成環境檢查、目錄創建和自我註冊。
- **指令：**
  ```bash
  ./install.sh
  ```

---
### 【第二類：專家獨立調用指令 (調試用)】

*在開發和調試過程中，用於單獨測試某個「專家」的功能。*

---

#### 調用「結構專家」(`engine.py`)
- **用途：** 在不通過主控制器的情況下，直接生成一個目錄的結構樹。
- **指令格式：** `python3 <專家路徑> <目錄路徑> [舊內容來源]`
- **示例 1 (掃描目錄，無舊註解)：**
  ```bash
  python3 src/core/engine.py ./src
  ```
- **示例 2 (掃描目錄，並從檔案讀取舊註解)：**
  ```bash
  python3 src/core/engine.py ./src ./README.md
  ```
- **示例 3 (掃描目錄，並從管道讀取舊註解)：**
  ```bash
  cat README.md | python3 src/core/engine.py ./src -
  ```

#### 調用「路徑專家」(`path.py`)
- **用途：** 獨立執行路徑的「讀、寫、驗證、淨化」操作。
- **指令格式：** `python3 <專家路徑> <命令> [參數...]`
- **示例 1 (驗證路徑是否存在)：**
  ```bash
  python3 src/core/path.py validate ./src/shell/control.sh ./README.md
  ```
- **示例 2 (讀取檔案內容)：**
  ```bash
  python3 src/core/path.py read ./README.md
  ```
- **示例 3 (淨化一個 Windows 路徑)：**
  ```bash
  python3 src/core/path.py normalize "D:\Obsidian_Vaults\Laplace_Notes"
  ```
- **示例 4 (淨化一個 WSL 網路路徑)：**
  ```bash
  python3 src/core/path.py normalize "//wsl.localhost/Ubuntu/home/serpal"
  ```

---
### 【第三類：開發與診斷指令】

*開發和測試週期中常用的輔助指令。*

---

#### 運行「診斷專家」(`diagnostics.sh`)
- **用途：** 執行所有自動化測試用例，檢查各模塊功能是否正常。
- **指令：**
  ```bash
  ./src/shell/diagnostics.sh
  ```

#### 清理哨兵環境
- **用途：** 強制殺死所有殘留的哨兵進程，並清理相關的日誌和 PID 文件。
- **指令：**
  ```bash
  pkill -f "inotifywait" || true && rm -f /tmp/sentry_*.pid && rm -f logs/sentry_*.log
  killall inotifywait
  ```

#### 實時查看日誌
- **用途：** 動態追蹤某個專案哨兵的日誌輸出。
- **指令格式：** `tail -f <日誌文件路徑>`
- **示例 (追蹤 `test` 專案的日誌)：**
  ```bash
  tail -f logs/sentry_test.log
  ```

---
### 【第四類：版本控制指令 (Git)】

*用於保存進度、回滾代碼和管理版本。*

---

#### 暫存所有變更
- **用途：** 將當前工作目錄下所有的修改、新增、刪除的文件，都放入 Git 的「待提交區」。
- **指令：**
  ```bash
  git add .
  ```

#### 提交變更
- **用途：** 將「待提交區」的所有內容，創建一個永久的快照（版本記錄）。
- **指令格式：** `git commit -m "類型: 做了什麼事"`
- **示例：**
  ```bash
  git commit -m "feat: 完成數據通道管道化改造"
  ```

#### **[新增]** 一鍵回滾 (撤銷未提交的修改)
- **用途：** 如果搞砸了，可以用此命令放棄對某個或某些文件的所有修改，將它們恢復到上一次提交時的狀態。
- **指令格式：** `git checkout -- <文件路徑1> <文件路徑2> ...`
- **示例 (一鍵恢復我們這次要修改的兩個文件)：**
  ```bash
  git checkout -- src/shell/control.sh src/shell/worker.sh
  ```

---

### 【第五類：臨時手動操作指令】

*在不使用 Git 等正式工具時，用於快速、臨時地保存和恢復工作。*

---

#### 手動備份文件
- **用途：** 在進行一次有風險的修改前，快速創建一個當前文件的副本作為臨時保險。
- **指令格式：** `cp <原始文件> <備份文件>`
- **示例 (備份我們這次要修改的兩個文件)：**
  ```bash
  cp src/shell/control.sh src/shell/control.sh.bak
  cp src/shell/worker.sh src/shell/worker.sh.bak
  ```

#### 手動恢復文件
- **用途：** 當修改失敗時，從之前創建的備份副本中恢復原始文件。
- **指令格式：** `cp <備份文件> <原始文件>`
- **示例 (從備份中恢復我們修改過的兩個文件)：**
  ```bash
  cp src/shell/control.sh.bak src/shell/control.sh
  cp src/shell/worker.sh.bak src/shell/worker.sh
  ```

---



## 專案結構

<!-- AUTO_TREE_START -->
laplace_sentry_control_v2/
├── _archive/                                 # 【存檔區】存放過時或不再使用的舊版本文件。
│   └── control.sh                            # 舊版本的 control.sh 腳本備份。
├── data/                                     # 【數據區】存放專案運行所需的持久化數據。
│   └── projects.json                         # 核心數據文件，以 JSON 格式存儲所有受監控專案的名單與配置。
├── logs/                                     # 【日誌區】存放哨兵運行時產生的所有日誌與進程文件。
│   ├── sentry_debug.log                      # 用於開發調試的通用日誌文件。
│   ├── sentry_laplace_sentry_control_v2.log  # 特定專案的哨兵日誌，記錄文件變動與更新詳情。
│   ├── sentry_run.log                        # 舊的運行日誌，可考慮清理。
│   ├── sentry_sentry_itself.log              # TODO: Add comment here
│   └── sentry_test.log                       # 診斷腳本專用的測試日誌。
├── src/                                      # 【源碼區】存放專案的所有核心邏輯代碼。
│   ├── core/                                 # 核心引擎區，存放純粹的、可獨立運行的 Python 專家模塊。
│   │   ├── engine.py                         # 【結構專家】負責生成目錄樹結構與合併註解的 Python 腳本。
│   │   └── path.py                           # 【路徑專家】負責所有文件 I/O 操作與跨平台路徑處理的 Python 腳本。
│   └── shell/                                # Shell 腳本區，存放負責流程控制與用戶交互的腳本。
│       ├── control.sh                        # 【管理專家】專案的總控制器，提供主菜單與所有用戶交互功能。
│       ├── control.sh.bak                    # TODO: Add comment here
│       ├── diagnostics.sh                    # 【診斷專家】自動化測試腳本，用於單元測試和集成測試。
│       ├── worker.sh                         # 【工人腳本】後台核心工作單元，由哨兵觸發，負責執行完整的更新流程。
│       └── worker.sh.bak                     # TODO: Add comment here
├── .gitignore                                # 【Git 忽略清單】告訴 Git 哪些文件或目錄不需要被版本控制。
├── 111                                       # TODO: Add comment here
├── README.md                                 # 【專案說明書】專案的入口文檔，提供高層次的介紹和使用說明。
├── releases.md                               # 【版本發布記錄】記錄每個公開版本的主要功能、變更和已知問題。
└── 三版本分析.md                                  # TODO: Add comment here
<!-- AUTO_TREE_END -->