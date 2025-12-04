
# **🆕《Laplace Sentry Control — Backend README（WSL 專用版）》**


# **1. 專案簡介（Overview）**

**Laplace Sentry Control System** 是一套針對本地環境設計的 **穩定、高可預測性目錄監控系統**。
後端（WSL）負責：

* 多專案監控（multi-sentry）
* 目錄快照與變化比對
* 靜默機制（SmartThrottler）
* 原子寫入（atomic write）
* 狀態檔輸出與審計能力
* 供前端 UI 呼叫的統一 CLI 入口

所有核心流程皆可審計、可測試、可預期。

---

# **2. 系統需求（WSL / Backend Requirements）**

### **作業系統**

* WSL（Ubuntu 或其他 Linux 發行版）
* Python 3.10+

### **第三方依賴（Runtime 必要）**

```
portalocker==3.2.0
```

> 註：pytest、pluggy、Pygments 等為「開發/測試依賴」，不包含在正式運行需求。

---

# **3. 安裝（Installation）**

```bash
git clone https://github.com/<your-repo>/laplace_sentry_control_v2.git
cd laplace_sentry_control_v2

python3 -m venv .venv
source .venv/bin/activate

pip install portalocker==3.2.0
```

---

# **4. 專案目錄結構（Backend Structure）**

```
laplace_sentry_control_v2/        # 專案根目錄（main.py 所在位置）
├── data/
│   └── projects.json             # 專案設定唯一來源
├── regression/                   # 自動化測試區（可選，不影響運行）
│
├── src/
│   └── core/                     # 後端核心邏輯（唯一正式模組）
│       ├── __init__.py
│       ├── daemon.py             # 管理生命週期、事件分派、PID
│       ├── engine.py             # 目錄樹生成、忽略規則
│       ├── formatter.py          # 輸出格式器（Markdown）
│       ├── io_gateway.py         # 原子寫入、安全 I/O 層
│       ├── path.py               # 路徑正規化 / 跨平台處理
│       ├── sentry_worker.py      # 哨兵監控流程
│       └── worker.py             # 單次更新執行器
│
├── main.py                       # 後端入口（WSL CLI）
├── PROTOCOL.md                   # 模組邊界與 API 契約（後端正式規範）
└── releases.md                   # 版本紀錄

```

---

# **5. 使用方式（Usage — WSL Backend）**

所有操作皆需 **在專案根目錄**（含 main.py）進行。

### **5.1 啟動主控制台（推薦）**

```bash
cd /path/to/laplace_sentry_control_v2
source .venv/bin/activate
python main.py
```

啟動後會出現互動式主選單，可執行：

* 新增 / 修改 / 刪除專案
* 啟動 / 停止哨兵
* 自由更新 / 手動更新
* 管理忽略規則
* 讀取事件日誌

---

# **5.2 CLI 指令（單次操作模式）**

若不使用互動式選單，可直接執行：

### **列出所有專案**

```bash
python main.py list_projects
```

### **新增專案**

```bash
python main.py add_project <project_dir> <output_md> [alias]
```

### **啟動 / 停止哨兵**

```bash
python main.py start_sentry <uuid>
python main.py stop_sentry <uuid>
```

### **讀取專案日誌**

```bash
python main.py get_log <uuid> [lines]
```

### **手動更新（啟動一次 worker 流程）**

```bash
python main.py manual_update <uuid>
```

### **新增忽略規則**

```bash
python main.py add_ignore_patterns <uuid>
```

---

# **6. 測試（Testing — Optional）**

若需執行完整測試套件：

```bash
pip install pytest
pytest
```

或執行指定模組：

```bash
python -m unittest regression.test_regression_suite_v8
```

---

# **7. 架構摘要（Architecture Summary）**

後端採五階層架構：

```
Client Layer → Daemon Layer → Worker Layer → Engine Layer
                        ↑
              io_gateway / path
```

詳見 `PROTOCOL.md`。

---

# **8. 授權（License）**

MIT License

---

# **9. 作者（Author）**

Developed by Par (帕爾)
Co-designed with Laplace / Raven Persona AI


