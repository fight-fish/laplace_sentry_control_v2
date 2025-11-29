# **README.md（v7.0）**

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

Sentry 專注於 **穩定性、可預期性、透明度與安全性**。
所有邏輯均可被測試、可審計、可追溯。

---

# # **2. 功能亮點（Features）**

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

### **✓ 可審計狀態檔（`.sentry_status`）**

* worker → daemon 單向溝通
* UI 不讀原始檔，只透過 daemon 取得狀態

### **✓ Sentry UI v1 (Windows GUI)**

* **Windows 系統匣常駐**：輕量化控制台，不佔用桌面空間
* **直覺操作**：支援拖曳新增專案（含一對多輸出支援）
* **完整控制**：右鍵選單支援刪除專案與手動更新
* **即時狀態**：雙擊即可啟停監控，狀態燈號即時同步（綠/黃/灰）

### **✓ Sentry UI v1 (Windows GUI)**

* **Windows 系統匣常駐**：輕量化控制台，不佔用桌面空間
* **直覺操作**：支援拖曳新增專案（含一對多輸出支援）
* **完整控制**：右鍵選單支援刪除專案與手動更新
* **即時狀態**：雙擊即可啟停監控，狀態燈號即時同步（綠/黃/灰）

---

# # **3. 安裝（Installation）**

```bash
git clone https://github.com/<your-repo>/laplace_sentry_control_v2.git
cd laplace_sentry_control_v2
pip install -r requirements.txt
```

若使用 watchdog：

```bash
pip install watchdog
```

---

# # **4. 專案目錄結構（Project Structure）**

<!-- AUTO_TREE_START -->
```
laplace_sentry_control_v2/           
├── data/                            
│   └── projects.json                # 【唯一真實來源】記錄所有受監控專案的設定資料（uuid、路徑、狀態）
│
├── regression/                      
│   ├── test_regression_suite_v8.py  # 【全域回歸測試】覆蓋專案增刪修查與完整生命週期
│   ├── test_sentry_persistence.py   # 【狀態持久化測試】逐一驗證 PID 與 .sentry_status 正確行為
│   └── test_throttler.py            # 【SmartThrottler 測試】全面測試高頻、批次與異常事件
│
├── src/                             
│   ├── core/                        
│   │   ├── __init__.py              # 標記 core 模組（無邏輯）
│   │   ├── daemon.py                # 【管理者】專案生命週期、啟停 worker、解析狀態、維護 projects.json
│   │   ├── engine.py                # 【邏輯引擎】純邏輯判定（事件分類、Throttler 判定、噪音分析）
│   │   ├── formatter.py             # 【輸出格式器】整理 list_projects() 輸出給 UI/CLI 使用
│   │   ├── io_gateway.py            # 【I/O 法務層】唯一允許進行檔案寫入的地方（atomic_write / safe_modify）
│   │   ├── path copy.py             # （待刪除？）舊版 path 模組的備份
│   │   ├── path.py                  # 【路徑工具】正規化路徑、絕對/相對判定、路徑對齊
│   │   ├── sentry_worker.py         # 【哨兵進程】監控檔案事件、與 engine 協作、寫入 .sentry_status
│   │   └── worker.py                # 【事件迴圈】負責事件 dispatch、整合 watchdog 與 throttler
│   │
│   └── ui/                          
│       └── ui_probe.py              # 【UI 原型】測試 GUI 通訊或 Tray 原型的實驗用腳本
│
├── .gitignore                       # Git 忽略設定（log、cache、pycache 等）
│
├── PROTOCOL.md                      # 【協定書】全系統的模組邊界、資料流、禁止規則（v4.0）
├── README.md                        # 【使用說明】快速上手、安裝、CLI 操作、目錄結構（v7.0）
├── main.py                          # 【客戶端入口】統一的 CLI 入口；UI 亦透過此層操作 daemon
└── releases.md                      # 【版本紀錄】系統演化歷史（v2.0）

```
<!-- AUTO_TREE_END -->


---

# # **5. 使用方式（Usage）**

所有指令都透過 `python main.py` 進行：

### ***進入虛擬環境*

```bash
source .venv/bin/activate
```

### **列出所有專案**

```bash
python -m src.main list_projects
```

### **新增專案**

```bash
python -m src.main add_project <project_dir> <output_file> [alias]
```

### **啟動某專案的哨兵**

```bash
python -m src.main start_sentry <uuid>
```

### **停止某專案的哨兵**

```bash
python -m src.main stop_sentry <uuid>
```

### **手動更新（驅動 worker）**

```bash
python -m src.main manual_update <uuid>
```

### **把靜默檔案加入 ignore 清單**

```bash
python -m src.main add_ignore_patterns <uuid>
```

---

# # **6. 測試（Testing）**

本專案的設計哲學是「行為先於實作」，
因此所有核心行為皆有對應測試。

### **執行全部測試：**

```bash
python -m unittest regression.test_regression_suite_v8 \
                   regression.test_sentry_persistence \
                   regression.test_throttler
```

若使用 pytest：

```bash
pytest
```

---

# # **7. 架構概念（Architecture Summary）**

Sentry 採用**五層架構**，以確保可測試性與高穩定性：

```
UI Layer → Client Layer → Daemon Layer → Worker Layer → Engine
                        ↑
                  io_gateway / path
```

* **UI Layer**：圖形介面。只負責顯示 / 輸入，不做邏輯
* **Client Layer**：解析輸入、輸出統一格式
* **Daemon Layer**：專案生命週期、PID 管理、解析 worker 訊號
* **Worker Layer**：watchdog + SmartThrottler
* **Engine Layer**：純邏輯，不依賴 I/O
* **I/O Layer**：atomic_write / path 正規化

詳細請見：`PROTOCOL.md v4.0`

---

# # **8. 版本記錄（Release Notes）**

完整歷史請見：`releases.md`

目前主要版本進展：

| 版本   | 主軸        | 說明                        |
| ---- | --------- | ----------------------         |
| v6.6 | UI 整合     | 右鍵選單、刪除、智慧新增        |
| v6.6 | UI 整合     | 右鍵選單、刪除、智慧新增        |
| v6.5 | 系統修復      | WSL 背景執行與 CLI 通訊修復   |
| v6.4 | Engine 重構 | 註釋系統、prefix 修復          |
| v6.3 | 靜默審計      | 狀態訊號 → ignore patterns   |
| v6.2 | 狀態檔       | worker → daemon 資料流建立    |
| v6.1 | 哨兵管理      | PID 自愈、手動更新            |
| v6.0 | 永生哨兵      | 多哨兵穩定版                  |

---

# # **9. 授權（License）**

MIT License
你可自由修改、再分發，請保留原作者註記。

---

# # **10. 作者（Author）**

Developed by **帕爾 (Par)**
Co-designed with **Laplace / Raven Persona** AI 協作模型。

---

