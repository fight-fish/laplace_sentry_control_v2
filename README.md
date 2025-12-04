# **README.md（v7.1）**

**Laplace Sentry Control System**
**A Deterministic, Auditable, and Stable Runtime Watchdog**

---

# # **1. 專案簡介（Overview）**

**Laplace Sentry Control System** 是一個為本地開發環境設計的 **高可靠度目錄監控系統**。
它提供：

* 多專案並行監控（multi-sentry）
* 精確到事件的 SmartThrottler
* 安全原子寫入（atomic I/O）
* 完整的專案生命週期管理
* 透過「狀態檔」提供可審計的監控訊號
* **[New] 視覺化日誌戰情中心 (Log Dashboard)**

Sentry 專注於 **穩定性、可預期性、透明度與安全性**。
所有邏輯均可被測試、可審計、可追溯。

---

# # **2. 功能亮點（Features）**

### **✓ Sentry UI v2 (The Living Eye)**

* **哨兵之眼 (The Eye)**：桌面常駐的生物感介面，支援呼吸、掃視與眨眼動畫。
* **意圖感知 (Intention Filter)**：
    * **Layer 1**：拖曳已註冊專案 → 自動識別並啟動/更新。
    * **Layer 2**：拖曳含 README 的新資料夾 → 自動填入並註冊。
    * **Layer 3**：拖曳未知資料夾 → 進入飢餓模式，引導餵食寫入檔。
* **日誌戰情室 (Log Dashboard)**：黑底白字的即時日誌螢幕，支援自動刷新與白話翻譯（Humanized Log）。
* **非阻斷式引導**：使用懸浮氣泡 (Status Bubble) 取代傳統彈出視窗。

### **✓ 多專案哨兵管理**

* 每個專案都有獨立的目錄監控
* 可個別啟動 / 停止
* 專案資訊以 `projects.json` 管理

### **✓ SmartThrottler（智慧靜默引擎）**

* 自動判定批次寫入 / 爆量事件
* 異常時自動進入靜默（muting）
* 回歸正常自動解除靜默
* 完整測試覆蓋（事件、體積、頻率）

### **✓ 安全且可預期的 I/O 層**

* atomic_write
* safe_read_modify_write
* 路徑正規化
* 嚴格模組邊界：任何模組不得跨層寫檔

---

# # **3. 安裝（Installation）**

```bash
git clone [https://github.com/](https://github.com/)<your-repo>/laplace_sentry_control_v2.git
cd laplace_sentry_control_v2
pip install -r requirements.txt

若使用 watchdog：

pip install watchdog

# 4. 專案目錄結構（Project Structure）

###  wsl端

laplace_sentry_control_v2/           # 【WSL 後端專案根目錄】
├── data/                            
│   └── projects.json                # 【唯一真實來源】記錄所有專案的設定 (UUID, Path, Status)
├── regression/                      # 【自動化測試區】
│   ├── test_path_normalize.py       # 【路徑測試】驗證 Windows/WSL 路徑轉換邏輯
│   ├── test_regression_suite_v8.py  # 【全域回歸】測試增刪修查與生命週期
│   ├── test_sentry_persistence.py   # 【持久化測試】驗證 PID 與狀態檔行為
│   └── test_throttler.py            # 【靜默測試】驗證 SmartThrottler (R1-R4) 觸發邏輯
├── src/                             # 【核心源碼區】
│   ├── core/                        
│   │   ├── __init__.py              # 【模組標記】
│   │   ├── daemon.py                # 【大腦】總管生命週期、分派指令 (get_log)、管理 PID
│   │   ├── engine.py                # 【邏輯引擎】純運算層 (目錄樹生成、忽略規則判定)
│   │   ├── formatter.py             # 【包裝工】將目錄樹轉為 Markdown 格式
│   │   ├── io_gateway.py            # 【海關】負責所有檔案原子寫入與鎖定 (Atomic Write)
│   │   ├── path.py                  # 【路徑專家】正規化路徑、跨平台路徑處理
│   │   ├── sentry_worker.py         # 【哨兵】Watchdog 監控進程，負責寫入帶時間戳記的日誌
│   │   └── worker.py                # 【生產線】協調 Engine 與 Formatter 執行單次更新
│   └── ui/                          
│       └── ui_probe.py              # 【實驗室】用於測試後端與 GUI 通訊的原型腳本
├── .gitignore                       # 【Git 忽略設定】排除 logs, temp, venv 等
├── PROTOCOL.md                      # 【憲法 v4.1】定義模組邊界與 API 契約 (含 get_log)
├── main.py                          # 【客戶端入口】CLI 介面，也是 UI 呼叫的統一窗口
└── releases.md                      # 【版本史 v2.0】詳細記錄 v6.0 ~ v7.1 的演進歷程

###  win端

Sentry_UI_v1/                    # 【Windows 專用 UI 專案根目錄】
├── src/                         # 【UI 主程式碼區】
│   ├── backend/                 # 【與後端（WSL / Sentry）溝通的橋接層】
│   │   ├── __init__.py          # 【標記 backend 為 Python 套件】
│   │   └── adapter.py           # 【翻譯官】負責路徑轉換、呼叫 WSL 指令 (get_log, toggle) 與解析回傳資料
│   └── tray/                    # 【UI 主模組：系統托盤與主控制台】
│       ├── tray_app.py          # 【v1.8 Legacy】舊版控制台入口 (僅作備份，不再維護)
│       └── v2_sandbox.py        # 【v2.0 Core】哨兵之眼 (View A) + 日誌戰情室 (View B) 的完整實作
├── ui_design_draft/             # 【UI 設計草稿區】
│   ├── sentry_ui_vertical.png   # 【直式布局草稿】
│   └── sentry_ui_wireframe.png  # 【橫式布局草稿】
├── UI_Strings_Reference.md      # 【v1.8 舊版】字串規範 (備份)
├── UI_Strings_Reference_v2.md   # 【v2.1 正式版】定義 Eye Tooltip、氣泡引導語、日誌翻譯字典
└── run_ui.bat                   # 【啟動腳本】快速啟動 v2_sandbox UI

# 5. 使用方式（Usage）
所有指令都透過 python -m src.main 進行：

進入虛擬環境

source .venv/bin/activate

列出所有專案

python -m src.main list_projects

新增專案

python -m src.main add_project <project_dir> <output_file> [alias]

啟動 / 停止哨兵

python -m src.main start_sentry <uuid>
python -m src.main stop_sentry <uuid>

讀取專案日誌 [New]

python -m src.main get_log <uuid> [lines]
# 例如: python -m src.main get_log xxxxx-xxxx 20 (讀取最後 20 行)

手動更新（驅動 worker）

python -m src.main manual_update <uuid>

把靜默檔案加入 ignore 清單

python -m src.main add_ignore_patterns <uuid>

# 6. 測試（Testing）
本專案的設計哲學是「行為先於實作」，因此所有核心行為皆有對應測試。

執行全部測試：

python -m unittest regression.test_regression_suite_v8 \
                   regression.test_sentry_persistence \
                   regression.test_throttler

# 7. 架構概念（Architecture Summary）
Sentry 採用五層架構，以確保可測試性與高穩定性：

UI Layer → Client Layer → Daemon Layer → Worker Layer → Engine
                        ↑
                  io_gateway / path

詳見：PROTOCOL.md v4.1

# 8. 版本記錄（Release Notes）
完整歷史請見：releases.md

版本,主軸,說明
v7.1,日誌系統,後端 API + 前端視覺化與翻譯機
v7.0,UI v2.0,哨兵之眼、雙視圖架構、生物感動畫
v6.7,修改與防禦,專案修改、自由輸入、路徑正規化
v6.6,UI 整合,右鍵選單、刪除、智慧新增
v6.5,系統修復,WSL 背景執行與 CLI 通訊修復
v6.0,永生哨兵,多哨兵穩定版

# 9. 授權（License）
MIT License 你可自由修改、再分發，請保留原作者註記。

# 10. 作者（Author）
Developed by 帕爾 (Par) Co-designed with Laplace / Raven Persona AI 協作模型。