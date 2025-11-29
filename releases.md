
# **releases.md（v2.0）**

**Laplace Sentry Control System — Release Notes**

---

# # **版本索引（Version Index）**

| 版本         | 主軸        | 關鍵變化                           |
| ---------- | --------- | ------------------------------ |
| **v6.6.0** | UI 整合     | 右鍵選單、刪除功能、重名自動重試 |
| **v6.6.0** | UI 整合     | 右鍵選單、刪除功能、重名自動重試 |
| **v6.5.0** | 系統修復    | WSL 背景執行與 CLI 通訊修復    |
| **v6.4.0** | Engine 重構 | prefix 修正、註釋系統、engine 邏輯清理     |
| **v6.3.0** | 靜默審計      | muting → ignore patterns 流程穩定化 |
| **v6.2.0** | 狀態檔       | worker → daemon 單向訊號建立         |
| **v6.1.0** | 哨兵管理強化    | 健康檢查、自我復原、PID 管控               |
| **v6.0.0** | 永生哨兵      | 多專案監控穩定版（multi-sentry）         |
| **v5.x**   | 遺留系統      | 舊版生命週期與不完整 worker 模組           |
| **v4.x**   | 初代雛形      | 實驗性 watcher＋尚未封裝 I/O           |

---

# ## **v6.6.0 — UI Full Control Integration**

**（2025-11-29）**

### **摘要**

本版本補齊了 Windows UI 對後端控制的最後一塊拼圖：**刪除與手動更新**。
使用者現在可以透過圖形介面完全掌控專案的生命週期（生、死、養），無需再依賴 CLI。

### **亮點**

* **右鍵選單**：支援在專案列表上按右鍵，執行「刪除專案」與「手動更新」。
* **安全刪除**：刪除前會彈出確認視窗，防止誤操作。
* **智慧新增**：新增專案時若遇重名，自動彈出更名對話框並重試，無需重新填寫。
* **Stub 移除**：全面移除介面上的 "(Stub)" 字樣，正式進入真實運作階段。

### **技術更新**

* **UI**：實作 `CustomContextMenu` 與 `QInputDialog` 互動邏輯。
* **Adapter**：新增 `delete_project` 與 `trigger_manual_update` 介面。
* **Integration**：驗證了 UI → Adapter → Daemon 的完整指令鏈路。

---

# ## **v6.6.0 — UI Full Control Integration**

**（2025-11-29）**

### **摘要**

本版本補齊了 Windows UI 對後端控制的最後一塊拼圖：**刪除與手動更新**。
使用者現在可以透過圖形介面完全掌控專案的生命週期（生、死、養），無需再依賴 CLI。

### **亮點**

* **右鍵選單**：支援在專案列表上按右鍵，執行「刪除專案」與「手動更新」。
* **安全刪除**：刪除前會彈出確認視窗，防止誤操作。
* **智慧新增**：新增專案時若遇重名，自動彈出更名對話框並重試，無需重新填寫。
* **Stub 移除**：全面移除介面上的 "(Stub)" 字樣，正式進入真實運作階段。

### **技術更新**

* **UI**：實作 `CustomContextMenu` 與 `QInputDialog` 互動邏輯。
* **Adapter**：新增 `delete_project` 與 `trigger_manual_update` 介面。
* **Integration**：驗證了 UI → Adapter → Daemon 的完整指令鏈路。

---

# ## **v6.5.0 — Sentry Background Fix (The Immortal Update)**

**（2025-11-29）**

### **摘要**

本版本徹底解決了哨兵在 WSL 背景執行（由 Windows UI 啟動）時的「瞬間崩潰」與「通訊失敗」問題。
標誌著 **WSL 後端與 Windows 前端協作鏈路** 的完全打通。

### **亮點**

* **不死哨兵**：解決了父進程退出導致子進程被連坐處決的問題。
* **雙模入口**：`main.py` 現在能自動識別是「人為操作」還是「機器呼叫」。
* **除錯可視化**：哨兵現在能大聲說出錯誤原因（stderr），不再沈默。

### **技術更新**

* **Daemon**：引入 `start_new_session=True` (setsid) 讓哨兵成為獨立守護進程。
* **Daemon**：引入全域 `log_file` 參照，防止 Python GC 過早關閉 I/O 通道。
* **Client**：`main.py` 新增 `sys.argv` 偵測，實現無頭模式（Headless Mode）支援。
* **Worker**：重構觸發邏輯，強制捕獲並解碼 `stderr`。

---

> v6 系列被視為：
> **Sentry 的正式成熟架構期（Stabilization Era）**

---

# # **v6 系列（穩定化世代）**

---

# ## **v6.4.0 — Engine Stability Update**

**（2025-11-22）**

### **摘要**

本版本專注於 Engine / Parser / Prefix 三個深層元件的穩定性。
核心目標是讓 worker 在高噪音場景下依然可以「完全可預期」。

### **亮點**

* 全面重寫 prefix 正規化邏輯
* 註釋系統（annotation system）導入，提升程式碼可審計性
* 修正 watch event 在特定路徑格式下的錯誤判定
* Engine 進行完整的行為收斂（normalization）

### **技術更新**

* 修正「路徑開頭符號不正確會造成 prefix mismatch」問題
* Engine 將所有事件進入單一判定路徑（single pipeline）
* 重寫部分 SmartThrottler 判定（體積上限、時間間隔）
* 精簡大量 legacy code

---

# ## **v6.3.0 — Muting → Ignore Patterns 固化流程**

**（2025-11-20）**

### **摘要**

本版本處理 Sentry 最重要的「噪音審計與自癒機制」。
目標是讓 muting 能真正清楚落地，並避免永遠停留在「黃燈」。

### **亮點**

* 正式定義 muting 流程（狀態確認 → 固化 → 回歸正常）
* Daemon 新增 `add_ignore_patterns`
* Worker 的 muted_paths 會被完整寫入 status file（可審計）

### **技術更新**

* Daemon 提供 UI-ready 的 muting 狀態輸出
* Worker 寫入 stable JSON array（不再使用臨時格式）
* 「ignored patterns」與「muted paths」首次區分為兩種概念
* ignore 由 daemon 控制、muting 由 worker 控制

---

# ## **v6.2.0 — Status File Introduction**

**（2025-11-14）**

### **摘要**

建立了 daemon 與 worker 之間的 **正式通訊協定**。
讓每個專案的 worker 能將自身狀態乾淨地回傳給 daemon。

### **亮點**

* `.sentry_status` 作為 worker → daemon 單向訊號
* 完整 JSON 格式（避免 race conditions）
* Daemon 在 `list_projects()` 解析 muting
* UI 未來不會讀 status file，只讀 daemon 的輸出

### **技術更新**

* status file 採用 atomic_write
* worker 停止時會自動清除 status file
* daemon 擁有「不存在即正常」邏輯

---

# ## **v6.1.0 — Sentry Management Upgrade**

**（2025-11-10）**

### **摘要**

本版本確立 Sentry 的「長期運作能力」。
加強哨兵生命週期、自我修復、PID 管控。

### **亮點**

* PID registry 改寫（避免重複啟動）
* worker crash 時 daemon 可感知
* 新增 `manual_update`（低階維修指令）

### **技術更新**

* worker 停止時自動清理監控資源
* daemon 列出專案時提供「running / stopped」明確狀態
* status 解析與 PID 解析合併為單一流程

---

# ## **v6.0.0 — Multi-Sentry Stable Release**

**（2025-10-30）**

### **摘要**

Sentry 首次達成「多專案監控」的穩定版本。
這是系統架構真正成熟的起點。

### **亮點**

* projects.json 成為唯一真實來源
* 每個專案擁有獨立 worker
* daemon 成為單一入口（官方協定）

### **技術更新**

* 專案新增 / 刪除 / 修改 全部具原子性
* 強化 ignore 與路徑正規化
* 完整支援 JSON-based 專案描述

---

# # **v5 系列（Legacy Age）**

> *此階段特點：無正式協定書、worker 行為不完整、
> I/O 層與商業邏輯混雜，屬於 Pre-Protocol 時代。*

---

## **v5.x — Unstable Multi-Module Prototype**

### **摘要**

* 初步嘗試多模組分離
* Worker / Daemon 還未真正脫鉤
* 缺乏 atomic_write
* ignore 邏輯還未獨立

### **備註**

此系列僅供歷史存檔，不建議回溯使用。

---

# # **v4 系列（Foundational Age）**

## **v4.x — Prototype Watcher**

### **摘要**

* 第一次引入 watchdog
* worker 線程模型尚不完整
* 無 PID
* 無 projects.json 生命週期
* 系統行為不可預期（高噪音場景下易崩）

---

# # **早期版本（Archive）**

下列版本為歷史研究用途，不再維護。

<details>
<summary>點擊展開 v1–v3 歷史紀錄</summary>

### **v3.x**

* 測試性 watcher
* 無協定書
* I/O 與邏輯耦合

### **v2.x**

* 單哨兵版本
* 無 SmartThrottler
* 基本事件顯示

### **v1.x**

* 最初的 file-watcher 實驗
* 非模組化
* 無結構

</details>


