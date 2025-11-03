#!/bin/bash
set -euo pipefail

echo "--- 正在執行契約測試：list_projects ---"

# --- 定義變數 ---
DAEMON_SCRIPT="src/core/daemon.py"
PROJECTS_FILE="data/projects.json"

# --- 準備一個假的 projects.json 文件用於測試 ---
# 使用 Here Document 來創建一個包含標準 JSON 內容的文件
cat <<'EOF' > "$PROJECTS_FILE"
[
  {
    "id": "proj_1",
    "name": "Project Alpha"
  }
]
EOF

# --- 執行測試 ---
echo "  [測試員]: 正在向廚房發送 'list_projects' 暗號..."
# 呼叫 daemon.py，並傳入 'list_projects' 指令
actual_response=$(python3 "$DAEMON_SCRIPT" list_projects)
echo "  [廚房]: 回應了: '$actual_response'"

# --- 斷言結果 ---
# 讀取我們剛剛創建的假文件的內容，作為預期結果
expected_response=$(cat "$PROJECTS_FILE")

if [ "$actual_response" == "$expected_response" ]; then
    echo "✅ PASS: 廚房正確返回了專案列表！"
    # 清理測試文件
    rm "$PROJECTS_FILE"
    exit 0
else
    echo "❌ FAIL: 廚房返回的專案列表不正確！"
    echo "  [預期]: '$expected_response'"
    echo "  [實際]: '$actual_response'"
    # 清理測試文件
    rm "$PROJECTS_FILE"
    exit 1
fi
