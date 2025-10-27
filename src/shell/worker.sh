#!/bin/bash
# ==============================================================================
#  Laplace Sentry Worker - 工人專家 v1.0
# ==============================================================================
#
#  【核心職責】
#  只做一件事：在一個完全非交互的背景環境中，執行一次完整的更新流程。
#
#  【架構設計說明 (Architectural Note)】
#  本腳本中的核心更新邏輯，是從 control.sh 的 run_update() 函式中
#  「有意地、策略性地」複製而來。
#
#  這樣做的核心原因是：為了徹底隔離「交互環境」與「非交互環境」。
#
#  - control.sh：作為「管理專家」，它運行在前台，需要處理複雜的菜單
#    和使用者輸入，其環境是「交互式」的。
#  - worker.sh：作為「工人專家」，它被哨兵(sentry)在背景調用，其
#    環境必須是 100%「非交互式」的，以杜絕任何因試圖讀取輸入而
#    導致的進程假死或阻塞。
#
#  通過創建這個職責單一的「工人」，我們確保了背景更新流程的絕對
#  穩定與可靠，即使這在一定程度上造成了程式碼的重複。在當前階段，
#  這種對「穩定性」的權衡，高於對「程式碼去重(DRY)」的追求。
#
# ==============================================================================
# set -x
set -euo pipefail

# --- 參數接收 ---
# 檢查是否傳入了足夠的參數
if [ "$#" -ne 2 ]; then
    echo "[工人錯誤] 需要傳入兩個參數：PROJECT_PATH 和 TARGET_DOC_PATH" >&2
    exit 1
fi
PROJECT_PATH=$1
TARGET_DOC_PATH=$2

# --- 依賴計算 ---
# 根據自己的位置，計算出依賴腳本的絕對路徑
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
ENGINE_SCRIPT_PATH="${SCRIPT_DIR}/../core/engine.py"
PATH_SCRIPT_PATH="${SCRIPT_DIR}/../core/path.py"

# 【核心修正】無論傳入的路徑是什麼格式，都在工人內部再次進行權威的絕對路徑淨化
ABSOLUTE_PROJECT_PATH=$(python3 "$PATH_SCRIPT_PATH" normalize "$PROJECT_PATH")
ABSOLUTE_TARGET_DOC_PATH=$(python3 "$PATH_SCRIPT_PATH" normalize "$TARGET_DOC_PATH")

# ==============================================================================
#  核心更新流程 (複製自 control.sh)
# ==============================================================================

echo "--- [工人] 開始執行更新 ---"
echo "  - 監控目標: ${PROJECT_PATH}"
echo "  - 輸出文件: ${TARGET_DOC_PATH}"

# 【終極修正】徹底分離 stdout 和 stderr，只捕獲純淨的數據
# 我們將 stderr 重定向到 /dev/null，讓它徹底閉嘴，只關心退出碼。

# 【終極修正】允許 read 命令失敗，並捕獲退出碼，避免 set -e 中斷腳本
read_result=$(python3 "$PATH_SCRIPT_PATH" read "$ABSOLUTE_TARGET_DOC_PATH" 2>/dev/null || true)

read_exit_code=$?
full_old_content=""

if [ "$read_exit_code" -eq 0 ]; then
    full_old_content=$read_result
elif [ "$read_exit_code" -ne 2 ]; then
    # 如果退出碼不是 2 (檔案不存在)，那就是一個真正的錯誤，必須報錯並中止！
    echo "[工人錯誤] 讀取舊內容時發生意外錯誤，退出碼: ${read_exit_code}" >&2
    exit 1
fi
# 如果退出碼是 2 (檔案不存在)，我們就什麼都不做，允許 full_old_content 保持為空。

# 2. 從舊內容中提取舊的目錄樹（用於解析註解）
old_tree_for_engine=""
start_marker="<!-- AUTO_TREE_START -->"
end_marker="<!-- AUTO_TREE_END -->"
if [[ "$full_old_content" == *"$start_marker"* ]]; then
    temp="${full_old_content#*$start_marker}"
    old_tree_for_engine="${temp%%$end_marker*}"
fi

# 3. 調用引擎專家，生成新的、帶有註解的目錄樹
#    我們將可能存在的舊註解，通過管道傳遞給引擎的標準輸入。
new_tree_content=$(echo "$old_tree_for_engine" | python3 "$ENGINE_SCRIPT_PATH" "$ABSOLUTE_PROJECT_PATH" "-")

if [ $? -ne 0 ]; then
    echo "[工人錯誤] 引擎專家在生成目錄樹時出錯。" >&2
    exit 1
fi

# 4. 將新生成的目錄樹，智能地拼接回原始文件的頭部和尾部之間
final_content=""
if [[ "$full_old_content" == *"$start_marker"* ]]; then
    # 場景：原始文件包含標記
    head="${full_old_content%%$start_marker*}"
    tail="${full_old_content#*$end_marker}"
    final_content=$(printf "%s%s\n%s\n%s%s" "$head" "$start_marker" "$new_tree_content" "$end_marker" "$tail")
else
    # 場景：原始文件不包含標記（可能是空檔案或已有其他內容）
    if [ -z "$full_old_content" ]; then
        # 如果是空檔案，直接寫入
        final_content=$(printf "%s\n%s\n%s" "$start_marker" "$new_tree_content" "$end_marker")
    else
        # 如果有其他內容，在末尾追加
        final_content=$(printf "%s\n\n%s\n%s\n%s" "$full_old_content" "$start_marker" "$new_tree_content" "$end_marker")
    fi
fi

# 5. 調用路徑專家，將最終的完整內容寫回目標文件
if ! python3 "$PATH_SCRIPT_PATH" write "$TARGET_DOC_PATH" "$final_content"; then
    echo "[工人錯誤] 路徑專家在寫入文件時出錯。" >&2
    exit 1
fi

echo "--- [工人] 更新成功完成！ ---"
exit 0
