# **PROTOCOL.md（v4.1）**

**Sentry Control System — Module Boundary & Communication Contract**

---

# # **1. 文件目的（Purpose）**

本文件是 **Sentry Control System**（下稱 Sentry）的
**唯一正式協定書（Protocol Specification）**。

它定義：

* 每個模組的 **責任邊界（Responsibility Boundary）**
* 模組之間的 **通訊契約（Communication Contract）**
* 哪些行為 **被允許（Allowed）**
* 哪些行為 **被禁止（Forbidden）**
* 在未來增加 **GUI 層（UI）** 時，接口如何保持穩定

本協定作為「系統憲法」，所有程式碼皆不得違反。

---

# # **2. 系統總覽（System Overview）**

Sentry 系統依照 **四層架構** 運作：

UI Layer → Client Layer → Daemon Layer → Worker Layer ↑ ↓ I/O Layer ← Engine Layer


每一層都有明確且不可跨越的責任：

| 層級           | 名稱                      | 責任                       |
| ------------ | ----------------------- | ------------------------ |
| UI Layer     | GUI / Tray App          | 顯示狀態、觸發指令，不做商業邏輯         |
| Client Layer | main.py                 | 管理使用者互動、封裝 CLI 指令        |
| Daemon Layer | daemon.py               | 管理所有專案、啟停哨兵、持久化資料        |
| Worker Layer | sentry_worker.py        | 監控檔案事件、執行 SmartThrottler |
| Engine Layer | engine.py               | 純邏輯：判斷事件、解析輸入、產出模式       |
| I/O Layer    | io_gateway.py / path.py | 唯一負責檔案讀寫的地方              |

---

# # **3. 模組責任邊界（Module Boundaries）**

## ## **3.1 UI Layer — GUI / Tray App（新增的正式層級）**

**責任：**

* 顯示專案狀態（running / stopped / muting）
* 點擊以啟動 / 停止哨兵
* 拖曳資料夾建立專案
* 顯示錯誤訊息（不解析錯誤原因）
* **顯示即時日誌（透過 API 獲取）**
* 絕不直接接觸檔案系統

**禁止：**

* ❌ 不直接呼叫 daemon 的內部函式
* ❌ 不直接讀 `.sentry_status`
* ❌ 不直接寫 `projects.json`

---

## ## **3.2 Client Layer — main.py（互動入口）**

**責任：**

* 封裝 CLI
* 驗證輸入格式
* 呼叫 daemon 提供的功能
* 控制輸出格式（JSON / 表格）

**禁止：**

* ❌ 不直接啟動 worker
* ❌ 不自行寫入資料
* ❌ 不產生 PID / status file

---

## ## **3.3 Daemon Layer — daemon.py（核心管控者）**

**責任：**

* 管理所有專案資料（create / edit / delete / list）
* 啟動 / 停止哨兵（sentry worker）
* 主導專案生命週期
* 解讀 worker 狀態檔（muting 狀態）
* **提供日誌讀取接口**
* 產生可供 UI 使用的 **統一資料格式**

**禁止：**

* ❌ 不監控檔案
* ❌ 不做 SmartThrottler 判斷
* ❌ 不直接修改檔案內容（所有寫入交給 io_gateway）

---

## ## **3.4 Worker Layer — sentry_worker.py（實際監控檔案的哨兵）**

**責任：**

* 使用 watchdog 監控目錄
* 把所有事件丟給 Engine 層進行分析
* 處理 **SmartThrottler**
* 更新 `.sentry_status`（列表形式 JSON）
* 當哨兵停止時，清理自身 resources

**禁止：**

* ❌ 不直接寫入 projects.json
* ❌ 不新增 ignore patterns
* ❌ 不直接操作資料夾內容

---

## ## **3.5 Engine Layer — engine.py（純邏輯層）**

**責任：**

* 分析事件
* 提供「適應型判定」結果：

  * `is_harmless`
  * `is_heavy_write`
  * `is_noise`
  * `should_mute`
* 不依賴任何檔案或狀態

**禁止：**

* ❌ 不觸碰檔案
* ❌ 不管理 PID
* ❌ 不讀任何環境變數
* ❌ 不依賴 OS

Engine 必須是「可抽換模組」。

---

## ## **3.6 I/O & Utilities Layer — io_gateway.py / path.py**

**責任：**

* 讀寫 `projects.json`
* atomic_write / safe_read_modify_write
* 正規化路徑
* 提供唯一的檔案 I/O 接口

**禁止：**

* ❌ 不參與商業邏輯
* ❌ 不執行監控行為
* ❌ 不做事件判定

---

# # **4. 通訊契約（Communication Contract）**

以下描述「資料如何在各層之間流動」。

---

## ## **4.1 一般操作流程：啟動哨兵**

UI → main.py → daemon.py → sentry_worker.py


| 階段 | 主體     | 行為                  |
| -- | ------ | ------------------- |
| 1  | UI     | 使用者點擊「啟動」           |
| 2  | Client | 呼叫 daemon 開啟哨兵      |
| 3  | Daemon | 產生 PID ⇒ 啟動 worker  |
| 4  | Worker | 監控開始、產生 status file |

---

## ## **4.2 事件流：檔案事件如何被解析**

watchdog → worker → engine → worker → .sentry_status → daemon → UI


詳細表格：

| 階段 | 行為                                 | 主體              |
| -- | ---------------------------------- | --------------- |
| 1  | 檔案事件（created/modified/deleted）     | watchdog        |
| 2  | 傳遞至事件迴圈                            | worker          |
| 3  | 使用 Engine 解析                       | worker + engine |
| 4  | SmartThrottler 決定是否 muting         | worker          |
| 5  | 更新 `.sentry_status`                | worker          |
| 6  | Daemon 在 `list_projects` 解析 muting | daemon          |
| 7  | UI 顯示黃色指示燈                         | UI              |

---

## ## **4.3 muting 恢復流程（自愈）**

worker → status file 空 → daemon → UI


| 符號 | 行為             |
| -- | -------------- |
| ✔  | worker 偵測異常消失  |
| ✔  | 清空 muted_paths |
| ✔  | 刪除 status file |
| ✔  | daemon 報告狀態為正常 |
| ✔  | UI 指示燈回到綠色     |

---

# # **5. 持久化契約（Persistence Contract）**

所有永久儲存的資料都由 I/O 模組負責。

---

## ## **5.1 projects.json（唯一真實來源）**

格式（範例）：

```json
[
  {
    "uuid": "abcd-1234",
    "name": "my_project",
    "path": "/home/xxx/project",
    "output_file": ["/home/xxx/project/out.log"],
    "status": "running"
  }
]

禁止：

❌ worker 寫入

❌ engine 寫入

❌ UI 直接操作

❌ 任意模組繞過 atomic_write 寫入

所有寫入必須透過：

io_gateway.safe_read_modify_write()

## 5.2 .sentry_status（worker → daemon 的單向訊號）
格式：

["/abs/path/file1", "/abs/path/file2"]

worker 產生

worker 清空

daemon 解析

UI 只能透過 daemon 得到「是否 muting」，不可見到實際路徑

# 6. 命令契約（Canonical Commands）

6.1 專案管理

指令,用途
add_project,新增專案
edit_project,修改目錄或寫入檔
delete_project,刪除專案
list_projects,輸出 UI 需要的完整狀態

---

6.2 哨兵控制

指令,用途
start_sentry <uuid>,啟動 worker
stop_sentry <uuid>,停止 worker / 清除 PID
manual_update <uuid>,手動驅動 worker（optional）

6.3 審計 / 靜默控制

指令,用途
add_ignore_patterns <uuid>,把 muting 訊號固化成忽略規則
reset_ignore_patterns,清空忽略清單（optional）

6.4 資訊與日誌查詢（新增）

指令,用途
get_log <uuid> [lines],讀取指定專案的日誌末端 (預設 50 行)

# 7. 錯誤契約（Error Contract）
錯誤一律分成三大類：

類型,定義
USER_ERROR,使用者操作錯誤（輸入、路徑不存在）
SYSTEM_ERROR,I/O 錯誤、權限、檔案損毀
INTERNAL_ERROR,程式碼錯誤、未預期狀況

UI 的責任：只顯示錯誤，不解釋原因。 Daemon 的責任：永遠丟明確的錯誤碼。

---

# 8. 禁止規則（Global Forbidden Rules）
所有層級都必須遵守：

❌ 不得跨層呼叫（UI 不能直接呼叫 worker）

❌ 不得繞過 io_gateway 寫任何資料

❌ 不得在 engine 中引用 OS、I/O、時間

❌ 不得在 worker 中修改 projects.json

❌ 不得讓 daemon 直接監控檔案

❌ 不得在 UI 中解析 status file

這是「系統安全邊界」，永遠不可跨越。

---

# 9. 附錄：資料流地圖（Data Flow Diagram）

                       ┌───────────────┐
                       │     UI Layer   │
                       └───────┬───────┘
                               │
                               ▼
                         main.py (Client)
                               │
                               ▼
                        daemon.py (Manager)
                               │
                 ┌─────────────┴──────────────┐
                 ▼                              ▼
         io_gateway.py (I/O)            sentry_worker.py (Watcher)
                 ▲                              │
                 │                              ▼
                 └────────────── engine.py ─────┘
