# 《專案通訊協定書 v3.2 (哨兵回歸版)》

**文件 ID:** `LAPLACE-SENTRY-PROTOCOL-V3.2`
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

|| 指令 (Command)          | 參數 (Arguments)              | 描述                                                                                               | 成功響應 (stdout)                                 |
| --------------------- | --------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------- |
| `ping`                | (無)                         | 檢測後端服務是否可達。                                                                                      | `PONG`                                        |
| `list_projects`       | (無)                         | 獲取所有已註冊專案的列表（包含實時狀態）。                                                                            | JSON：`[ { "name": "...", "status": "..." } ]` |
| `add_project`         | `name` `path` `output_file` | 新增一個專案。                                                                                          | `OK`                                          |
| `edit_project`        | `uuid` `field` `new_value`  | 修改一個現有專案。                                                                                        | `OK`                                          |
| `delete_project`      | `uuid`                      | 刪除指定專案。                                                                                          | `OK`                                          |
| `manual_update`       | `uuid`                      | 手動觸發一次指定專案的更新。                                                                                   | `OK`                                          |
| `manual_direct`       | `project_path` `target_doc` | 直接對指定路徑執行一次更新。                                                                                   | `OK`                                          |
| `start_sentry`        | `uuid`                      | 為指定專案啟動背景監控哨兵。                                                                                   | `OK`                                          |
| `stop_sentry`         | `uuid`                      | 停止指定專案的背景監控哨兵。                                                                                   | `OK`                                          |
| `get_muted_paths`     | `uuid`                      | 讀取指定專案的暫存靜默路徑（`.sentry_status`），回傳目前被智能靜默標記的路徑列表。                                                | JSON：`["/path/one", "/path/two"]`             |
| `add_ignore_patterns` | `uuid`                      | 依據暫存靜默路徑推導出可固化的 ignore patterns（例如 `logs`, `tmp`），並寫回 `projects.json`；成功固化後會刪除 `.sentry_status`。 | JSON：`["logs", "tmp"]`                        |

