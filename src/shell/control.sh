#!/bin/bash
# 我們用 "#!/bin/bash" 來告訴系統，這是一個 Bash 腳本。

# --- 嚴格模式 ---
set -e

echo "--- 正在啟動『管理專家』(control.sh)... ---"

# ---【核心】水電驗證：從 Shell 呼叫 Python ---

echo "--- 正在嘗試呼叫『結構專家』(Python 引擎)... ---"

# 我們定義一個變數，存放 Python 引擎腳本的相對路徑。
# "$(dirname "$0")" 會得到 "src/shell"，所以我們需要先回到上一層 (..)，再進入 "core"。
PYTHON_ENGINE_SCRIPT="$(dirname "$0")/../core/structure_engine.py"

# 我們用「python3」指令來執行我們的 Python 腳本。
# 執行後的輸出結果，會被儲存到一個叫「engine_output」的變數裡。
engine_output=$(python3 "$PYTHON_ENGINE_SCRIPT")

# 最後，我們把從 Python 引擎那裡收到的「返回訊息」，打印到終端上。
echo "$engine_output"

echo "--- ✅ 『管理專家』(control.sh) 執行完畢。 ---"
