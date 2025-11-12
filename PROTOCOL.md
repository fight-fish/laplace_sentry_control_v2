【提案 17.4 修訂版 v2：專業化版本描述】
版本號： v8.1.0
版本代號： Guardian
版本類型： 功能與健-壯性更新 (Feature & Robustness Update)
版本描述:
本版本實現了完整的哨兵生命週期管理，並顯著增強了系統的狀態監控與容錯能力。通過對後端服務 daemon.py 的重構，引入了基於「進程存活性」與「路徑有效性」的雙重健康檢查機制，確保了狀態報告的準確性與持久性。前端 main.py 的交互流程也已同步升級，以支持對哨兵的菜單化管理和多維度狀態的可視化。
✨ 核心變更 (Core Changes):
【功能】哨兵生命週期管理:
[新增] 在 daemon.py 中實現了 handle_start_sentry 和 handle_stop_sentry 函式，使用 subprocess.Popen 對 sentry_worker.py 子進程進行背景化管理。
[新增] 實現了將子進程的 stdout 和 stderr 重定向到 logs/ 目錄下對應專案日誌文件的功能。
[新增] 在 main.py 中，將哨兵管理操作（啟動/停止）集成到 _select_project 表格化選擇菜單中。
【健壯性】狀態監控與自愈機制:
[重構] 重構了 daemon.py 的 handle_list_projects 函式，對所有已註冊專案執行「路徑有效性」檢查，並對運行中的哨兵執行「PID 存活性」檢查。
[新增] 引入了「殭屍自愈」邏輯：當健康檢查失敗時，系統會自動終止失效的子進程，並將其從 running_sentries 狀態字典中移除。
[修正] 解決了 invalid_path 狀態無法持久化顯示的問題，確保了前端狀態與後端真實情況的一致性。
[新增] 在 handle_start_sentry 中增加了對專案路徑的前置有效性驗證，防止啟動無效的哨兵進程。
【修正與優化】:
[修正] 修正了 sentry_worker.py 啟動日誌中，監控目錄路徑打印不準確的問題。
[修正] 修正了因 handle_list_projects 內部邏輯不完善，導致在特定場景下返回數據無法被 main.py 正確解析的問題。
🛠️ 技術性結論 (Technical Conclusions):
狀態管理: 確立了由 handle_list_projects 作為系統狀態的唯一權威報告來源，所有狀態檢查與自愈邏輯均收斂於此。
前後端契約: daemon.py 現在通過 status 欄位 (running, stopped, invalid_path)，向 main.py 提供了一套清晰、明確的狀態契約。

# 《專案通訊協定書 v3.1 (基線版)》

**文件 ID:** `LAPLACE-SENTRY-PROTOCOL-V3.1`
**狀態:** `生效中`
**核心原則:** 本文件是專案內部所有 Python 模組間通信的**唯一真理來源**。所有內部 API、數據流和異常處理，都必須嚴格遵循此處的定義。

---

## **第一章：全局規則與定義**

### **1.1 內部 API 設計原則**

-   **異常驅動 (Exception-Driven):** 模組間的錯誤傳遞，**必須**通過拋出具體的異常（如 `ValueError`, `IOError`）來實現。成功時，函式可以返回數據或隱式返回 `None`。
-   **類型提示 (Type Hinting):** 所有函式的參數和返回值，**必須**提供清晰的類型提示。
-   **依賴注入 (Dependency Injection):** 核心業務邏輯函式應允許通過可選參數傳入其依賴項，以實現可測試性。

### **1.2 數據持久化**

-   所有對文件系統的**讀寫操作**，**必須**通過 `io_gateway.py` 提供的 `safe_read_modify_write` 函式進行。

---

## **第二章：C/S 通信契約 (Client-Server Contract)**

本章定義了前端 (`main.py`) 與後端 (`daemon.py` 的 `main_dispatcher`) 之間，當前已實現的命令行風格指令。

| 指令 (Command) | 參數 (Arguments) | 描述 | 成功響應 (stdout) |
| :--- | :--- | :--- | :--- |
| `ping` | (無) | 檢測後端服務是否可達。 | `PONG` |
| `list_projects` | (無) | 獲取所有已註冊專案的列表。 | `[ { "name": "...", ... } ]` (JSON) |
| `add_project` | `name` `path` `output_file` | 新增一個專案。 | `OK` |
| `edit_project` | `uuid` `field` `new_value` | 修改一個現有專案。 | `OK` |
| `delete_project` | `uuid` | 刪除一個指定的專案。 | `OK` |
| `manual_update` | `uuid` | 手動觸發一次指定專案的更新。 | `OK` |
| `manual_direct` | `project_path` `target_doc` | 直接對指定路徑執行一次更新。 | `OK` |

---
【修改說明】
版本號更新: 將版本更新為 v3.1 (基線版)，以反映這是一個穩定的、基礎的版本。
移除未實現指令: 從指令表格中，完全移除了 start_sentry, stop_sentry, get_ignore_patterns, update_ignore_patterns 等所有我們尚未開發的指令。
簡化描述: 刪除了所有與「哨兵」和「雙軌制」相關的、超前的架構描述和 Mermaid 流程圖，讓文件聚焦於當前的現實。