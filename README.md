```markdown
# 通用目錄哨兵控制中心 (Laplace Sentry Control)

本專案旨在打造一個可移植、可擴展的通用開發者文檔自動化工具。

---

## 指揮中心儀表板 (Command Palette)

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

#### **[新增]** 調用「結構專家」
- **用途：** 在不通過主控制器的情況下，直接、手動地生成一個指定目錄的結構樹，並將結果打印到終端。
- **指令格式：** `python3 <結構專家路徑> <要掃描的目錄路徑>`
- **示例 (掃描我們的測試樣板房)：**
  ```bash
  python3 src/core/structure_engine.py ./test_scaffold
  ```

---

開發流程
存檔指令
git add .
git commit -m "類型(範圍): 做了什麼事"

清理環境

pkill -f "inotifywait" || true
rm -f /tmp/sentry_test.pid
rm -f logs/sentry_test.log
rm -rf test_scaffold/*

查看日誌
cat logs/sentry_test.log

---

## 專案結構

<!-- AUTO_TREE_START -->
laplace_sentry_control_v2/
├── backups/                              # TODO: Add comment here
├── data/                                 # TODO: Add comment here
│   └── projects.json                     # TODO: Add comment here
├── logs/                                 # TODO: Add comment here
├── src/                                  # TODO: Add comment here
│   ├── core/                             # TODO: Add comment here
│   │   ├── engine.py                     # TODO: Add comment here
│   │   └── path.py                       # TODO: Add comment here
│   └── shell/                            # TODO: Add comment here
│       ├── control.sh                    # TODO: Add comment here
│       └── diagnostics.sh                # TODO: Add comment here
├── test_data/                            # TODO: Add comment here
│   └── expected_control_flow_output.txt  # TODO: Add comment here
├── watchers/                             # TODO: Add comment here
├── 代碼避難所/                                # TODO: Add comment here
│   ├── path_engine.v1_for_control_sh.py  # TODO: Add comment here
│   └── structure_engine.py               # TODO: Add comment here
├── .gitignore                            # TODO: Add comment here
├── README.md                             # TODO: Add comment here
├── install.sh                            # TODO: Add comment here
├── mock_readme.md                        # TODO: Add comment here
└── 三版分析.md                               # TODO: Add comment here
<!-- AUTO_TREE_END -->