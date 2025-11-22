版本發布記錄 (Release Log)


v6 系列（Sentry Persistence & Intelligent Muting Line）
v6.4.0 — Engine Stability Update (2025-11-22)

版本類型：核心穩定性總重構 (Engine Stability & Annotation Refactor)

產品摘要（Product Summary）

重大引擎重構版本。全面修復目錄樹順序、註釋消失、段落對齊、忽略規則衝突等核心問題，使目錄輸出邏輯回到穩定、可靠、可預期的狀態。此版本奠定未來「智能註釋」與「路徑語意分析」等進階功能所需的底層基座。

工程更新（Engineering Details）
【目錄樹生成器重構】

_generate_tree() 完成系統性重寫：

採用 VSCode-style 原生順序（資料夾 → 檔案 → 原順序保持）

拆分為 tree_lines（視覺行）與 tree_nodes（路徑 key）

遞迴 prefix、branch、縮排策略全面修復

行距、空白行、尾部與對齊全部重新定義

【註釋系統升級：Path-Key Annotation Model】

廢棄舊視覺行比對法（易破裂）

以 path-key（例如 src/core/engine.py）作為註釋定位基準

註釋在「移動、重命名、重組」後仍可正確綁定

新增 basename fallback，避免極端同名節點衝突

【ignore_patterns 與引擎整合】

移除舊 SYSTEM_DEFAULT_IGNORE 硬編碼

前端管理的 ignore_patterns 與引擎完全一致

修復「設定了但沒有生效」的歷史 bug

【技術債清理】

刪除舊型註釋處理函式（_parse_comments / _merge_and_align_comments）

移除未使用的 v4 遺留函式

刪除整包 tests/ 舊測試資料夾

【穩定性修復】

修復深層遞迴 prefix 破裂問題

修復 TODO 與使用者註釋混淆

手動壓力測試涵蓋：檔案搬移／重命名／層級調整／忽略規則切換

v6.3.0 — The Auditor Bridge (2025-11-20)

版本類型：智能靜默審計與規則固化 (Muting Audit & Rule Hardening)

產品摘要

讓哨兵的「暫時靜默」真正能被管理者審查、批准、並永久固化成 ignore rules。此版本正式打通「動態防禦」→「永久防火牆」的閉環。

工程更新
【狀態讀取與審計入口】

新增 handle_get_muted_paths(uuid) — 讀取 .sentry_status

handle_list_projects 支援專案狀態 muting

【規則固化與清理】

handle_add_ignore_patterns()：

從 muted paths 推導出忽略規則

更新 projects.json

自動清理 .sentry_status

【前端審查流程】

新增 [8] 審查系統建議：

顯示處於靜默的專案

顯示靜默路徑

一鍵固化 → 專案狀態恢復

v6.2.0 — The Signal Beacon (2025-11-18)

版本類型：信號發布與防禦增強 (Signal Emission & Safety Reinforcement)

產品摘要

哨兵學會「發送自己的狀態訊號」。所有智能靜默相關資訊會寫入 .sentry_status，供 daemon 解析。並修復關鍵性的「輸出文件觸發無限迴圈」缺陷。

工程更新

哨兵偵測 muted_paths 變化 → 寫入 JSON status file

加入 OUTPUT-FILE-BLACKLIST 避免監控迴圈

handle_start_sentry() 增加輸出文件黑名單傳遞

v6.1.0 — The Vigilant Guardian (2025-11-18)

版本類型：健壯性與防禦強化

產品摘要

加強哨兵生命週期管理：健康檢查、自愈機制、狀態同步。

工程更新

新增 handle_start_sentry / handle_stop_sentry

日誌重導向至 logs/

加入殭屍哨兵自動清理

加入無效路徑偵測

v6.0.0 — The Immortal Sentry (2025-11-14)

版本類型：核心架構里程碑（Persistent Sentry Framework）

產品摘要

哨兵從「易死」變成「永生」。引入 PID registry，使哨兵生命週期可追蹤、可恢復、可自愈。

工程更新

引入 .sentry PID registry system

周期性人口普查（health check）

自動清理殭屍 PID

哨兵忽略 SIGINT（Ctrl+C）避免被誤殺

v5 系列（Basecamp → Documentation Revolution → Engine Overhaul）
v5.3.0 — Engine Stability Update（2025-11-22）

版本類型：引擎穩定性革命

已收錄於 v6.4.0，避免重複，此處省略。整併為 v6.4.0。

v5.1.0 — Documentation Overhaul (2025-11-03)

版本類型：文檔與可讀性重構

產品摘要

全面統一註釋風格與註解哲學，將程式碼本身升級為「教學文檔」。

工程更新

所有核心腳本套用「極簡融合式」註解風格

引入 HACK / DEFENSE / COMPAT / FUTURE 等標籤

程式碼首次成為「可自我解釋」的知識資產

v5.0.0 — Basecamp (2025-11-03)

版本類型：C/S 架構奠基

產品摘要

從 shell → Python 架構全面跨越，確立了長期演進的核心骨架。

工程更新

main.py 成為唯一入口

建立雙陣列資料模型

daemon.py 完成 CRUD 與安全性檢查

恢復手動更新功能

v4 系列（Phoenix Rebirth）
v4.0.0 — Phoenix (2025-10-28)

版本類型：穩定性與正確性修正

產品摘要

完全根治中文註釋消失問題，回歸視覺模式匹配哲學。

工程更新

移除不穩定的相對路徑註釋策略

回歸視覺行匹配演算法

建立 stdin 安全管道

強化 worker.sh flock 機制

v1 系列（MVP 原始奠基）
v1.0.0 — MVP (2025-10-27)

版本類型：最小可行產品

產品摘要

通用目錄哨兵控制中心首次具備完整功能閉環。

工程更新

完整名單管理

哨兵系統啟動/停止流程

自動建立輸出文件

初版 Diagnostics 測試框架