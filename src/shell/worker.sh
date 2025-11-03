#!/bin/bash
# ==============================================================================
#  Laplace Sentry Worker - 工人腳本 v1.3 (穩定版)
# ==============================================================================
#
#  【核心職責】
#  在一個完全非交互的背景環境中，執行一次完整的、原子化的更新流程。
#
#  【v1.3 穩定版 - 架構設計說明】
#  本腳本的設計，是基於 v1.x 開發階段中，對系統穩定性問題進行深度
#  診斷後的最終架構。它嚴格遵循了「穩定性優先」的設計原則，並在
#  其基礎上，完成了三大核心架構升級：
#
#  1. 【數據通道重構：從文件 I/O 到標準輸入流】
#     - 早期版本 (v1.0) 的工人腳本需要自行調用 I/O 模塊讀取文件，
#       這在跨系統的高延遲場景下，被證實是導致「進程阻塞」的根源。
#     - 穩定版 (v1.3) 的數據來源被嚴格限定為「標準輸入 (stdin)」。
#       它不再依賴文件系統的讀取狀態，只處理從管道流入的數據流。
#       這一改造，從根本上解決了 I/O 阻塞的風險。
#
#  2. 【專家協同模式升級：引入「格式化專家」】
#     - 為適配 Obsidian 等不同終端的渲染要求，我們遵循「關注點分離」
#       原則，引入了全新的「格式化專家 (formatter.py)」。
#     - 工作流從「內容生成 -> 寫入」，升級為更專業的
#       「內容生成 (engine) -> 格式化 (formatter) -> 寫入 (path)」，
#       實現了「數據模型」與「視圖表現」的徹底解耦。
#
#  3. 【健壯性增強：輸入內容預處理】
#     - 在引入「格式化」層後，為確保核心引擎接收到的數據是純淨的，
#       我們在數據流的早期階段增加了對輸入內容的預處理邏輯。
#     - 此舉修正了因「雙重格式化」可能導致的「註解解析失敗」問題。
#
#  本腳本的演進歷史，是整個專案從「原型」到「可靠」的技術縮影。
#  它代表了我們對「系統穩定性」的嚴格要求，和對「模塊化架構」的工程實踐。
#
# ==============================================================================

# TODO: 在未來實現全 Python 工作流後，這個 worker.sh 腳本將被徹底廢棄。
# 屆時，set -x 追蹤日誌的功能也需要遷移到 Python 的 logging 模組中。
# set -x

# DEFENSE: 這是 Shell 腳本的「安全模式」配置。
# - `set -e`: 讓腳本在遇到任何命令返回非零退出碼時，立刻中止執行。
# - `set -u`: 當使用未定義的變數時，立刻報錯並中止。
# - `set -o pipefail`: 在管道命令中，只要有任何一個環節失敗，就將整個管道的退出碼設為失敗時的退出碼。
set -euo pipefail

# --- 參數接收與依賴路徑計算 ---

# DEFENSE: 檢查傳入的參數數量（$#）是否不等於（-ne）2。
if [ "$#" -ne 2 ]; then
    # 如果不符合，向標準錯誤流（>&2）輸出錯誤訊息，並以狀態 1 退出。
    echo "[工人錯誤] 需要傳入兩個參數：PROJECT_PATH 和 TARGET_DOC_PATH" >&2
    exit 1
fi
# 將第一個參數（$1）賦值給變數 PROJECT_PATH。
PROJECT_PATH=$1
# 將第二個參數（$2）賦值給變數 TARGET_DOC_PATH。
TARGET_DOC_PATH=$2

# HACK: 這裡通過相對路徑計算，來定位其他專家腳本的絕對路徑。
# 這確保了無論從何處調用此腳本，它總能找到其依賴的模塊。
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
ENGINE_SCRIPT_PATH="${SCRIPT_DIR}/../core/engine.py"
PATH_SCRIPT_PATH="${SCRIPT_DIR}/../core/path.py"
FORMATTER_SCRIPT_PATH="${SCRIPT_DIR}/../core/formatter.py"
LOCK_FILE="${SCRIPT_DIR}/../../logs/.worker.lock"

# --- 核心數據流：從標準輸入讀取完整的原始文件內容 ---
# 我們用「cat」命令，讀取從「管道（pipe）」傳入的全部標準輸入流，並存入變數。
full_old_content=$(cat)

# ==============================================================================
#  核心更新流程 (穩定版)
# ==============================================================================
# DEFENSE: 使用子 Shell `()` 和 flock 文件鎖，實現操作的原子性和互斥性。
# 這確保了同一時間只有一個更新流程在執行，防止競態條件。
(
# 在執行任何操作前，嘗試獲取一個非阻塞的（-n）排他鎖。
# 如果獲取失敗（鎖已被其他進程持有），則記錄訊息並以狀態 0 正常退出。
flock -n 200 || { echo "【工人】獲取鎖失敗，另一個實例正在運行。本次操作跳過。" >&2; exit 0; }

echo "--- [工人] 開始執行更新流程 (v1.3) ---"
echo "  - 掃描目錄: ${PROJECT_PATH}"
echo "  - 輸出目標: ${TARGET_DOC_PATH}"

# 1. 【內容生成】調用結構專家 (engine.py)
#    將完整的舊內容（full_old_content）通過管道（|）傳遞給「結構專家（engine.py）」。
#    專家負責解析舊註解，並生成新的、合併了註解的目錄樹內容。
new_tree_content=$(echo "$full_old_content" | python3 "$ENGINE_SCRIPT_PATH" "$PROJECT_PATH" "-")
# DEFENSE: 檢查上一條命令的退出碼（$?），如果不為 0，則報錯退出。
if [ $? -ne 0 ]; then
    echo "[工人錯誤] 結構專家 (engine.py) 在生成目錄樹時返回錯誤。" >&2
    exit 1
fi

# 2. 【格式化】調用格式化專家 (formatter.py)
#    將純淨的目錄樹內容通過管道傳遞給「格式化專家（formatter.py）」，進行特定格式的封裝。
formatted_tree_block=$(echo "$new_tree_content" | python3 "$FORMATTER_SCRIPT_PATH" --strategy obsidian)
if [ $? -ne 0 ]; then
    echo "[工人錯誤] 格式化專家 (formatter.py) 在格式化時返回錯誤。" >&2
    exit 1
fi

# 3. 【內容拼接】根據標記，智能地替換或追加內容
final_content=""
start_marker="<!-- AUTO_TREE_START -->"
end_marker="<!-- AUTO_TREE_END -->"
# 判斷舊內容中是否包含（== *...*）開始標記。
if [[ "$full_old_content" == *"$start_marker"* ]]; then
    # 如果包含，則使用 Shell 的參數擴展功能，精準地切分出頭部（head）和尾部（tail）。
    head="${full_old_content%%$start_marker*}"
    tail="${full_old_content#*$end_marker}"
    # 使用 printf 命令，將「頭部 + 開始標記 + 新內容 + 結束標記 + 尾部」安全地拼接起來。
    final_content=$(printf "%s%s\n%s\n%s%s" "$head" "$start_marker" "$formatted_tree_block" "$end_marker" "$tail")
else
    # 如果不包含標記，則進一步判斷舊內容是否為空（-z）。
    if [ -z "$full_old_content" ]; then
        # 如果為空，則直接生成「開始標記 + 新內容 + 結束標記」。
        final_content=$(printf "%s\n%s\n%s" "$start_marker" "$formatted_tree_block" "$end_marker")
    else
        # 如果不為空，則在舊內容的末尾，追加一個空行和新的內容塊。
        final_content=$(printf "%s\n\n%s\n%s\n%s" "$full_old_content" "$start_marker" "$formatted_tree_block" "$end_marker")
    fi
fi

# 4. 【文件寫入】調用路徑專家 (path.py)
#    將最終拼接好的內容（final_content）通過管道，交給「路徑專家（path.py）」執行寫入操作。
echo "$final_content" | python3 "$PATH_SCRIPT_PATH" write "$TARGET_DOC_PATH"
if [ $? -ne 0 ]; then
    echo "[工人錯誤] 路徑專家 (path.py) 在寫入文件時返回錯誤。" >&2
    exit 1
fi

echo "--- [工人] 更新流程成功完成。 ---"

# 此處的 `) 200>"$LOCK_FILE"` 與開頭的 `flock` 配套使用，它將文件描述符 200 重定向到鎖文件。
) 200>"$LOCK_FILE"

# 以成功的狀態（0）退出腳本。
exit 0
