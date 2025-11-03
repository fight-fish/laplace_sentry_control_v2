#!/bin/bash
# 終極考卷：add_project v2 - 全場景驗收測試
# 注意：我們故意移除了 'set -e'，以確保所有測試場景都會被執行

echo "================================================="
echo "  「add_project」命令全場景驗收測試"
echo "================================================="

# --- 準備工作 ---
# 1. 定義我們的「後廚」和「菜單本」的路徑
DAEMON_SCRIPT="src/core/daemon.py"
PROJECTS_FILE="data/projects.json"

# 2. 定義一個輔助函式，用於在每次測試前，都清空「菜單本」
#    確保每次考試，都是從一張白紙開始
reset_projects_file() {
    echo "  [準備]: 正在清空 data/projects.json..."
    echo "[]" > "$PROJECTS_FILE"
}

# 3. 定義一個輔助函式，用於呼叫後廚，並打印結果
#    這是我們的「傳菜員」
call_daemon() {
    echo "-------------------------------------------------"
    echo "  > 正在呼叫後廚，指令: python3 $DAEMON_SCRIPT $@"
    python3 "$DAEMON_SCRIPT" "$@"
    echo "-------------------------------------------------"
}

# --- 正式開始考試 ---

# 考試 1：正常添加一個絕對路徑的、不存在的專案
echo -e "\n--- 測試 1: 正常添加 (應成功) ---"
reset_projects_file
# 我們需要一個真實存在的絕對路徑來做測試
# pwd 命令可以獲取當前工作目錄的絕對路徑
EXISTING_ABS_PATH=$(pwd)/src 
EXISTING_MD_ABS_PATH=$(pwd)/README.md
call_daemon add_project "NormalProject" "$EXISTING_ABS_PATH" "$EXISTING_MD_ABS_PATH"
echo "  > 請驗收：上方是否打印了 'OK'？"

# 考試 2：添加一個相對路徑的專案
echo -e "\n--- 測試 2: 添加相對路徑 (應失敗) ---"
reset_projects_file
call_daemon add_project "RelativePathProject" "src" "README.md"
echo "  > 請驗收：上方是否打印了 'ERROR: All paths must be absolute paths.'？"

# 考試 3：添加一個不存在路徑的專案
echo -e "\n--- 測試 3: 添加不存在的路徑 (應失敗) ---"
reset_projects_file
NON_EXISTENT_PATH=$(pwd)/no_such_dir
call_daemon add_project "NonExistentPathProject" "$NON_EXISTENT_PATH" "$EXISTING_MD_ABS_PATH"
echo "  > 請驗收：上方是否打印了 'ERROR: Path validation failed'？"

# 考試 4：添加一個重名的專案
echo -e "\n--- 測試 4: 添加重名專案 (應失敗) ---"
reset_projects_file
# 先成功添加一次
call_daemon add_project "DuplicateName" "$EXISTING_ABS_PATH" "$EXISTING_MD_ABS_PATH" > /dev/null
# 再嘗試用同樣的名字添加一次
call_daemon add_project "DuplicateName" "$(pwd)/tests" "$(pwd)/releases.md"
echo "  > 請驗收：上方是否打印了 'ERROR: Project name ... already exists'？"

# 考試 5：添加一個重複路徑的專案
echo -e "\n--- 測試 5: 添加重複路徑 (應失敗) ---"
reset_projects_file
# 先成功添加一次
call_daemon add_project "ProjectA" "$EXISTING_ABS_PATH" "$EXISTING_MD_ABS_PATH" > /dev/null
# 再嘗試用不同的名字，但同樣的路徑，添加一次
call_daemon add_project "ProjectB" "$EXISTING_ABS_PATH" "$(pwd)/releases.md"
echo "  > 請驗收：上方是否打印了 'ERROR: Project path ... is already being watched'？"

echo -e "\n================================================="
echo "  所有考試場景已執行完畢。"
echo "================================================="
