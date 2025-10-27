#!/bin/bash
# ==============================================================================
#  Laplace Sentry Worker - 工人專家 v1.3 (鳳凰涅槃版)
# ==============================================================================
#
#  【核心職責】
#  只做一件事：在一個完全非交互的背景環境中，執行一次完整的更新流程。
#
#  【v1.3 鳳凰涅槃版 - 架構設計說明】
#  本腳本的設計，是我們在經歷了【階段零】史詩級除錯戰役後，所有
#  血淚經驗的最終結晶。它嚴格遵循了從 v1.0 繼承而來的、關於「穩
#  定性」的最高憲法，並在其基礎上，完成了三大核心進化：
#
#  1. 【數據通道革命：從自主 I/O 到管道輸入】
#     - 原始版 (v1.0) 的工人需要自己調用 path.py 來讀取文件，這在
#       跨系統的高延遲場景下，被證明是導致「進程卡死」的根源。
#     - 鳳凰涅槃版 (v1.3) 的工人，其數據來源被嚴格限定為「標準輸入
#       (stdin)」。它不再關心數據從哪裡來，只關心處理從管道流入的
#       數據。這一改造，徹底根除了 I/O 阻塞的風險。
#
#  2. 【專家協同進化：引入「格式化專家」】
#     - 為了適配 Obsidian 等不同終端的顯示要求，我們拒絕了在工人
#       內部硬編碼格式的「髒活」，而是引入了全新的「格式化專家
#       (formatter.py)」。
#     - 工人的工作流，從「生產 -> 物流」，升級為了更專業的
#       「生產 (engine) -> 打包 (formatter) -> 物流 (path)」，
#       實現了「內容」與「表現」的徹底分離。
#
#  3. 【健壯性補丁：「拆包裝」邏輯】
#     - 在引入「打包 (formatter)」後，我們發現需要一個對應的「拆
#       包裝」環節，以確保 engine.py 收到的永遠是純淨的食材。
#     - 本版本在處理舊內容時，增加了一個精巧的「拆包裝」步驟，
#       修正了因「雙重包裝」導致的「註解丟失」問題。
#
#  本腳本的演進史，就是我們整個專案從「能用」到「可靠」的縮影。
#  它代表了我們對「穩定性」的最高敬畏，和對「優雅架構」的不懈追求。
#
# ==============================================================================
#set -x
set -euo pipefail

# --- 參數接收與依賴計算 ---
if [ "$#" -ne 2 ]; then
    echo "[工人錯誤] 需要傳入兩個參數：PROJECT_PATH 和 TARGET_DOC_PATH" >&2
    exit 1
fi
PROJECT_PATH=$1
TARGET_DOC_PATH=$2

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
ENGINE_SCRIPT_PATH="${SCRIPT_DIR}/../core/engine.py"
PATH_SCRIPT_PATH="${SCRIPT_DIR}/../core/path.py"
FORMATTER_SCRIPT_PATH="${SCRIPT_DIR}/../core/formatter.py"

# --- 核心改造：從標準輸入讀取【完整的、原始的】舊內容 ---
full_old_content=$(cat)

# ==============================================================================
#  核心更新流程 (終極版)
# ==============================================================================
echo "--- [工人] 開始執行更新 (終極版) ---"
echo "  - 監控目標: ${PROJECT_PATH}"
echo "  - 輸出文件: ${TARGET_DOC_PATH}"

# 1. 【終極撥亂反正】
#    我們不再自己做任何提取！直接將【完整的、原始的】full_old_content
#    通過管道，交給 engine.py 去處理！
new_tree_content=$(echo "$full_old_content" | python3 "$ENGINE_SCRIPT_PATH" "$PROJECT_PATH" "-")
if [ $? -ne 0 ]; then
    echo "[工人錯誤] 結構專家 (engine.py) 在生成目錄樹時出錯。" >&2
    exit 1
fi

# 2. 調用【格式化專家】，對「原材料」進行「打包」
formatted_tree_block=$(echo "$new_tree_content" | python3 "$FORMATTER_SCRIPT_PATH" --strategy obsidian)
if [ $? -ne 0 ]; then
    echo "[工人錯誤] 格式化專家 (formatter.py) 在格式化時出錯。" >&2
    exit 1
fi

# 3. 將「打包好」的成品，智能地拼接回原始文件的頭部和尾部之間
final_content=""
start_marker="<!-- AUTO_TREE_START -->"
end_marker="<!-- AUTO_TREE_END -->"
if [[ "$full_old_content" == *"$start_marker"* ]]; then
    head="${full_old_content%%$start_marker*}"
    tail="${full_old_content#*$end_marker}"
    final_content=$(printf "%s%s\n%s\n%s%s" "$head" "$start_marker" "$formatted_tree_block" "$end_marker" "$tail")
else
    if [ -z "$full_old_content" ]; then
        final_content=$(printf "%s\n%s\n%s" "$start_marker" "$formatted_tree_block" "$end_marker")
    else
        final_content=$(printf "%s\n\n%s\n%s\n%s" "$full_old_content" "$start_marker" "$formatted_tree_block" "$end_marker")
    fi
fi

# 4. 調用【路徑專家】，將最終的「成品」安全地寫入目標文件
echo "$final_content" | python3 "$PATH_SCRIPT_PATH" write "$TARGET_DOC_PATH"
if [ $? -ne 0 ]; then
    echo "[工人錯誤] 路徑專家 (path.py) 在寫入文件時出錯。" >&2
    exit 1
fi

echo "--- [工人] 更新成功完成！ ---"
exit 0

