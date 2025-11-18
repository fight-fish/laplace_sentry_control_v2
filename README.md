# Laplace Sentry Control

[![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-v6.0.0-brightgreen.svg )](releases.md)

一個基於 Python 的、通用的、可自動監控目錄變化並更新文檔的哨兵控制中心。

---

## ✨ 核心功能

- **📝 智能目錄樹生成：** 自動掃描專案結構，生成美觀的、可自定義忽略規則的目錄樹。
- **🛡️ 實時哨兵監控：** 在背景中啟動獨立的哨兵進程 (`sentry_worker.py`)，實時監控文件變化並觸發自動更新。
- **⚙️ 命令行驅動：** 提供功能豐富的交互式主菜單 (`main.py`) 和強大的後端直接調用能力 (`daemon.py`)。
- **⚖️ 健壯的 I/O 網關：** 所有文件操作均通過集中的、帶有文件鎖的 I/O 網關進行，確保在高併發下的數據絕對安全。
- **🧪 自動化回歸測試：** 內置基於 `unittest` 的回歸測試套件，實現對核心「增、刪、改、查」功能的「一鍵體檢」。

## 🚀 快速上手

#### 1. 克隆倉庫
```bash
git clone https://github.com/fight-fish/laplace_sentry_control_v2.git
cd laplace_sentry_control_v2
```

#### 2. 安裝依賴
(建議在 Python 虛擬環境中執行)
```bash
pip install -r requirements.txt
```

#### 3. 啟動主菜單
```bash
python main.py
```
現在，您可以通過交互式菜單，開始管理您的第一個專案了！

## 🛠️ 核心指令詳解

**重要：** 所有直接調用後端的指令，都必須在專案的根目錄下，使用 `python -m <模塊路徑>` 的格式執行，以確保 Python 能夠正確處理模塊間的導入。

攻擊測試指令

ATTACK_FILE="attack_test.log"; echo ">>> 準備發起高頻寫入攻擊 <<<"; for i in $(seq 1 20); do echo "Attack wave $i" >> "$ATTACK_FILE"; sleep 0.05; done; echo ">>> 攻擊結束。請檢查哨兵日誌。 <<<"; rm "$ATTACK_FILE";


#### 列出所有專案
```bash
python -m src.core.daemon list_projects
```

#### 手動更新指定專案
```bash
# 1. 先用 list_projects 獲取專案的 UUID
# 2. 將下面的 <UUID> 替換為您要更新的真實 UUID
python -m src.core.daemon manual_update 7cbcd3cb-ec7c-4263-ac9a-f20e6cc95b7d
```

#### 啟動/停止哨兵
```bash
# 1. 先用 list_projects 獲取專案的 UUID
# 2. 將下面的 <UUID> 替換為您要操作的真實 UUID

# 啟動哨兵
python -m src.core.daemon start_sentry 7cbcd3cb-ec7c-4263-ac9a-f20e6cc95b7d

# 停止哨兵
python -m src.core.daemon stop_sentry 7cbcd3cb-ec7c-4263-ac9a-f20e6cc95b7d
```

## 🔬 開發與測試

我們歡迎任何形式的貢獻！在提交您的更改之前，請確保通過了內置的回歸測試。

**運行核心功能回歸測試：**
```bash
python -m unittest regression/test_regression_suite_v8.py
```

## 📜 許可證

本專案採用 [MIT License](https://opensource.org/licenses/MIT) 授權。
```
---


```markdown
<!-- AUTO_TREE_START -->
```
laplace_sentry_control_v2/
├── data/                                         # 【數據區】存放專案運行所需的持久化資料 (已被 .gitignore 忽略)。
│   └── projects.json                             # 【專案名單】以 JSON 格式記錄所有受監控專案與設定。
├── logs/                                         # 【日誌區】存放哨兵運行時產生的日誌文件 (已被 .gitignore 忽略)。
│   ├── .gitkeep                                  # TODO: Add comment here
│   ├── 自主開發.log                                  # TODO: Add comment here
│   └── 自動目錄.log                                  # TODO: Add comment here
├── regression/                                   # 【回歸測試套件】存放用於保證核心功能穩定性的自動化測試。
│   ├── test_multiprocessing_communication.py     # (待辦) 用於測試多進程通信的腳本。
│   ├── test_regression_suite_v8.py               # 【核心測試資產】v8 架構下的「增刪改查」完整生命週期回歸測試。
│   ├── test_sentry_persistence.py                # TODO: Add comment here
│   └── test_throttler.py                         # TODO: Add comment here
├── src/                                          # 【源碼區】存放專案的所有核心程式碼。
│   └── core/                                     # 【核心業務邏輯】
│       ├── __init__.py                           # TODO: Add comment here
│       ├── daemon.py                             # 【守護進程】作為後端服務，處理所有業務邏輯的總指揮官。
│       ├── engine.py                             # 【結構專家】負責生成目錄結構樹的核心算法。
│       ├── formatter.py                          # 【格式專家】(歷史資產) 負責格式化輸出內容。
│       ├── io_gateway.py                         # 【I/O 網關】處理所有文件讀寫，並提供文件鎖，確保數據安全。
│       ├── path.py                               # 【路徑專家】提供路徑淨化、驗證等工具。
│       ├── sentry_worker.py                      # 【哨兵工人】被獨立啟動的背景進程，負責監控文件變化。
│       ├── sentry_worker_backup.py               # TODO: Add comment here
│       └── worker.py                             # 【更新工人】被守護進程調用，執行單次的目錄掃描與文件更新。
├── temp/                                         # TODO: Add comment here
│   ├── .gitkeep                                  # TODO: Add comment here
│   ├── 1601868.sentry                            # TODO: Add comment here
│   ├── 1649304.sentry                            # TODO: Add comment here
│   ├── BDD Agent設計.md.20251118-134813.bak        # TODO: Add comment here
│   ├── BDD Agent設計.md.20251118-134817.bak        # TODO: Add comment here
│   ├── BDD Agent設計.md.20251118-134842.bak        # TODO: Add comment here
│   ├── README.md.20251118-150221.bak             # TODO: Add comment here
│   ├── README.md.20251118-150953.bak             # TODO: Add comment here
│   ├── README.md.20251118-151506.bak             # TODO: Add comment here
│   ├── projects.json.20251118-151730.bak         # TODO: Add comment here
│   ├── projects.json.20251118-151757.bak         # TODO: Add comment here
│   ├── projects.json.20251118-151845.bak         # TODO: Add comment here
│   ├── tests_readme.md.20251118-094700.bak       # TODO: Add comment here
│   ├── tests_readme.md.20251118-094702.bak       # TODO: Add comment here
│   └── tests_readme.md.20251118-094704.bak       # TODO: Add comment here
├── tests/                                        # TODO: Add comment here
│   ├── tests/                                    # TODO: Add comment here
│   │   └── test_daemon_to_worker_integration.py  # TODO: Add comment here
│   ├── 35351                                     # TODO: Add comment here
│   ├── fake_expert_sleeps.py                     # TODO: Add comment here
│   ├── grg                                       # TODO: Add comment here
│   ├── node_modules                              # TODO: Add comment here
│   ├── readme                                    # TODO: Add comment here
│   ├── test_atomic_write.py                      # TODO: Add comment here
│   ├── test_daemon_integration.py                # TODO: Add comment here
│   ├── test_file_lock.py                         # TODO: Add comment here
│   ├── test_timeout.py                           # TODO: Add comment here
│   ├── test_worker_workflow.py                   # TODO: Add comment here
│   └── tests_readme.md                           # TODO: Add comment here
├── .gitignore                                    # 【Git 忽略列表】告訴 Git 哪些文件或目錄不應被納入版本控制。
├── PROTOCOL.md                                   # (歷史資產) 記錄了早期的設計決策與通信協議。
├── README.md                                     # 【項目門面】您正在閱讀的、向世界介紹本專案的文件。
├── main.py                                       # 【主入口】用戶交互的命令行界面 (CLI)，專案的唯一啟動入口。
└── releases.md                                   # TODO: Add comment here
```
<!-- AUTO_TREE_END -->
```
