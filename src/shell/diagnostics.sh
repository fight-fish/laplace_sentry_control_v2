#!/bin/bash
# ==============================================================================
#  通用目錄哨兵 - 診斷專家 (diagnostics.sh)
#  版本: 3.0 (穩定版 - 移除不穩定的哨兵測試)
# ==============================================================================
set -euo pipefail
TOTAL_TESTS=0
FAILED_TESTS=0
ENGINE_SCRIPT_PATH="src/core/engine.py"
PATH_SCRIPT_PATH="src/core/path.py"

assert_equals() {
    local description=$1; local actual=$2; local expected=$3; local test_num=$4
    ((TOTAL_TESTS++))
    if [ "$actual" == "$expected" ]; then
        echo -e "  [${test_num}] ✅ PASS: ${description}"
    else
        echo -e "  [${test_num}] ❌ FAIL: ${description}\n     [預期]: $expected\n     [實際]: $actual"
        ((FAILED_TESTS++))
    fi
}

test_engine() {
    echo -e "\n--- 正在執行「引擎專家 (engine.py)」整合測試 ---"# 新的、絕對安全的臨時路徑
local TEST_SCAFFOLD_PATH="./diag_scaffold_engine"; 
rm -rf "$TEST_SCAFFOLD_PATH"; mkdir -p "$TEST_SCAFFOLD_PATH/src"; touch "$TEST_SCAFFOLD_PATH/README.md"

    local MOCK_README_PATH="/tmp/diag_mock_readme.md"; echo -e "<!-- AUTO_TREE_START -->\nsrc/ # old comment\n<!-- AUTO_TREE_END -->" > "$MOCK_README_PATH"
    local expected; local actual
    expected=$'diag_scaffold_engine/\n├── src/\n└── README.md'
    actual=$(python3 "$ENGINE_SCRIPT_PATH" "$TEST_SCAFFOLD_PATH" "None")
    assert_equals "基礎目錄樹生成" "$actual" "$expected" "1/3"
    expected=$'diag_scaffold_engine/\n├── src/         # old comment\n└── README.md    # TODO: Add comment here'
    actual=$(python3 "$ENGINE_SCRIPT_PATH" "$TEST_SCAFFOLD_PATH" "$MOCK_README_PATH")
    assert_equals "註解合併與對齊" "$actual" "$expected" "2/3"
    expected=$'diag_scaffold_engine/\n└── README.md'
    actual=$(python3 "$ENGINE_SCRIPT_PATH" "$TEST_SCAFFOLD_PATH" "None" "0" "1")
    assert_equals "深度控制" "$actual" "$expected" "3/3"
}

test_path_validation() {
    echo -e "\n--- 正在執行「尋路專家 (path.py) - validate 命令」單元測試 ---"
    python3 "$PATH_SCRIPT_PATH" validate "src/core" >/dev/null 2>&1; exit_code=$?
    assert_equals "驗證存在的路徑" "$exit_code" "0" "1/2"
    python3 "$PATH_SCRIPT_PATH" validate "/path/not/exist" >/dev/null 2>&1; exit_code=$?
    assert_equals "驗證不存在的路徑" "$exit_code" "2" "2/2"
}

test_path_normalize() {
    echo -e "\n--- 正在執行「尋路專家 (path.py) - normalize 命令」單元測試 ---"
    local actual; local expected
    actual=$(python3 "$PATH_SCRIPT_PATH" normalize "\\\\wsl.localhost\\Ubuntu\\home\\serpal")
    expected="/home/serpal"
    assert_equals "轉換 Windows UNC 路徑" "$actual" "$expected" "1/2"
    actual=$(python3 "$PATH_SCRIPT_PATH" normalize "D:\\Notes")
    expected="/mnt/d/Notes"
    assert_equals "轉換 Windows 磁碟機路徑" "$actual" "$expected" "2/2"
}

test_flock_concurrency() {
    echo -e "\n--- 正在執行「工人腳本 (worker.sh) - flock 併發鎖」壓力測試 ---"
    local WORKER_SCRIPT_PATH="src/shell/worker.sh"
    local LOG_DIR="logs"
    local LOCK_FILE="$LOG_DIR/.worker.lock"

    # 確保鎖文件在測試前不存在，避免干擾
    rm -f "$LOCK_FILE"

    # 1. 在後台啟動一個「慢工人」，它會獲取鎖並持有 3 秒
    # 我們用一個簡單的 flock 命令來模擬一個正在長時間運行的 worker
    (
        flock 200
        echo "慢工人已獲取鎖，將持有 3 秒..."
        sleep 3
        echo "慢工人已釋放鎖。"
    ) 200>"$LOCK_FILE" &

    # 記錄慢工人的進程 ID，以便後續等待
    local slow_worker_pid=$!

    # 給慢工人一點時間，確保它能先啟動並獲取鎖
    sleep 0.5

    # 2. 現在，嘗試啟動我們真正的 worker.sh（快工人）
    # 我們期望它會因為獲取不到鎖而立刻失敗並退出
    # 我們將它的標準錯誤輸出捕獲到 a_fast_worker_output 變量中
    # 注意：我們傳遞的是無意義的參數，因為我們只關心它是否被鎖住，不關心它是否能成功執行
    local actual_fast_worker_output
    actual_fast_worker_output=$(echo '{"project_path":"/tmp", "target_doc_path":"/tmp/doc"}' | bash "$WORKER_SCRIPT_PATH" "/tmp" "/tmp/doc" 2>&1)

    # 3. 斷言「快工人」的輸出是否包含了我們期望的「勸退」信息
    local expected_output_substring="獲取鎖失敗，另一個實例正在運行。優化性退出。"
    if [[ "$actual_fast_worker_output" == *"$expected_output_substring"* ]]; then
        actual="contains_expected_substring"
        expected="contains_expected_substring"
    else
        actual="$actual_fast_worker_output"
        expected="包含 '$expected_output_substring' 的字符串"
    fi
    assert_equals "併發的 worker.sh 應被 flock 阻止並優雅退出" "$actual" "$expected" "1/1"

    # 清理戰場：等待後台的慢工人進程結束
    wait "$slow_worker_pid"
    rm -f "$LOCK_FILE"
}


# --- 主執行區 ---
echo "--- 正在執行「通用目錄哨兵」核心單元測試 ---"
test_engine
test_path_validation
test_path_normalize
test_flock_concurrency

echo -e "\n----------------------------------------"
if [ "$FAILED_TESTS" -eq 0 ]; then
    echo "🎉 全部 $TOTAL_TESTS 個核心單元測試均已通過！"
else
    echo "🔥 共 $TOTAL_TESTS 個測試，有 $FAILED_TESTS 個失敗。"
fi
echo "----------------------------------------"
exit "$FAILED_TESTS"
