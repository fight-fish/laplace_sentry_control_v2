#!/bin/bash
# 注意：我們故意移除了 'set -e'

DAEMON_SCRIPT="src/core/daemon.py"
PROJECTS_FILE="data/projects.json"

echo "================================================="
echo "  契約測試：add_project (v2 - 寫入測試)"
echo "================================================="
echo

# --- 準備工作：確保測試環境是乾淨的 ---
echo "  [準備]: 正在創建一個乾淨的、空的 projects.json..."
echo "[]" > "$PROJECTS_FILE"


# --- 測試場景 1: 嘗試添加一個有效的新專案 ---
echo
echo "--- 測試場景 1: 添加一個有效專案 ---"
echo "  (預期結果：daemon.py 應返回 'OK')"
echo "-------------------------------------------------"

# 執行指令，這次我們期望它成功
# 我們使用一個真實存在的路徑 "src/core"
response=$(python3 "$DAEMON_SCRIPT" add_project "MyCore" "src/core" "docs/core.md" 2>&1)

echo "  > daemon.py 的回應是： '$response'"
echo "-------------------------------------------------"
echo "  請您判斷，上方回應是否為 'OK'？"
echo


# --- 測試場景 2: 檢查 projects.json 是否被正確寫入 ---
echo "--- 測試場景 2: 驗證 data/projects.json 文件內容 ---"
echo "  (預期結果：文件應包含我們剛剛添加的 'MyCore' 專案)"
echo "-------------------------------------------------"
echo "  > 當前 data/projects.json 的內容是："
# 使用 jq 來美化輸出，如果 jq 不存在，就直接 cat
if command -v jq &> /dev/null; then
    jq '.' "$PROJECTS_FILE"
else
    cat "$PROJECTS_FILE"
fi
echo "-------------------------------------------------"
echo "  請您判斷，上方內容是否包含了 'MyCore' 專案？"
echo

# --- 測試場景 3: 嘗試添加一個重名的專案 ---
echo "--- 測試場景 3: 添加一個重名專案 ---"
echo "  (預期結果：daemon.py 應返回『名稱已存在』的錯誤)"
echo "-------------------------------------------------"

error_response=$(python3 "$DAEMON_SCRIPT" add_project "MyCore" "src/shell" "docs/shell.md" 2>&1)

echo "  > daemon.py 的回應是： '$error_response'"
echo "-------------------------------------------------"
echo "  請您判斷，上方回應是否包含了 'Project name already exists'？"
echo

echo "================================================="
echo "  驗收結束。"
echo "================================================="
