#!/bin/bash
# Laplace Sentry Control - 管理專家
# 版本: 2.4.9 (穩定版 - 已移除不穩定的哨兵功能)

# --- 嚴格模式與全域變數 ---
set -euo pipefail
trap 'echo "【管理專家錯誤】: 錯誤發生在 ${BASH_SOURCE[0]} 的第 ${LINENO} 行" >&2' ERR

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
ENGINE_SCRIPT_PATH="${SCRIPT_DIR}/../core/engine.py"
PATH_SCRIPT_PATH="${SCRIPT_DIR}/../core/path.py"
# 如果外部通過第二個參數傳入了設定檔路徑，就用它；否則，使用預設路徑。
PROJECTS_FILE=${2:-"${SCRIPT_DIR}/../../data/projects.json"}

LOGS_DIR="${SCRIPT_DIR}/../../logs"



# --- 環境初始化 ---
mkdir -p "$LOGS_DIR"
if [ ! -f "$PROJECTS_FILE" ] || ! jq -e 'if type == "array" then true else false end' "$PROJECTS_FILE" > /dev/null 2>&1; then
    echo "[]" > "$PROJECTS_FILE"
fi



# ==============================================================================
#  UI 函式區 (使用者介面)
# ==============================================================================

show_main_menu() {
    clear
    echo "========================================"
    echo "   通用目錄哨兵 - 控制中心 v2.4.9"
    echo "========================================"
    echo "  [1] 列出所有專案"
    echo "  [2] 新增一個專案"
    echo "  [3] 修改一個專案"
    echo "  [4] 刪除一個專案"
    echo "----------------------------------------"
    echo "  [u] 手動觸發一次更新..."
    echo "----------------------------------------"
    echo "  [q] 退出系統"
    echo "========================================"
    echo -n "請輸入您的選擇: "
}

# ==============================================================================
#  核心功能函式區
# ==============================================================================

abort_with_msg() {
    echo -e "\n❌ \e[31m錯誤: $1\e[0m" >&2
    read -n 1 -s -r -p "按任意鍵返回..."
    return 1
}



run_update() {
    local project_path=$1
    local target_doc_path=$2
    
    echo "--- 開始執行手動更新 ---"
    echo "  - 監控目標: ${project_path}"
    echo "  - 輸出文件: ${target_doc_path}"

    local head tail start_marker end_marker
    start_marker="<!-- AUTO_TREE_START -->"
    end_marker="<!-- AUTO_TREE_END -->"

    local full_old_content
    full_old_content=$(python3 "$PATH_SCRIPT_PATH" read "$target_doc_path" || true)

    local old_tree_for_engine=""
    if [[ "$full_old_content" == *"$start_marker"* ]]; then
        local temp="${full_old_content#*$start_marker}"
        old_tree_for_engine="${temp%%$end_marker*}"
    fi

    local new_tree_content
    new_tree_content=$(echo "$old_tree_for_engine" | python3 "$ENGINE_SCRIPT_PATH" "$project_path" "-")
    if [ $? -ne 0 ]; then
        abort_with_msg "引擎專家在生成目錄樹時出錯。" || return
    fi

    local final_content
    if [[ "$full_old_content" == *"$start_marker"* ]]; then
        head="${full_old_content%%$start_marker*}"
        tail="${full_old_content#*$end_marker}"
        final_content=$(printf "%s%s\n%s\n%s%s" "$head" "$start_marker" "$new_tree_content" "$end_marker" "$tail")
    else
        if [ -z "$full_old_content" ]; then
            final_content=$(printf "%s\n%s\n%s" "$start_marker" "$new_tree_content" "$end_marker")
        else
            final_content=$(printf "%s\n\n%s\n%s\n%s" "$full_old_content" "$start_marker" "$new_tree_content" "$end_marker")
        fi
    fi
    
    if ! python3 "$PATH_SCRIPT_PATH" write "$target_doc_path" "$final_content"; then
        abort_with_msg "路徑專家在寫入文件時出錯。" || return
    fi
    echo "✅ 更新成功完成！"
    return 0
}

manual_update() {
    clear
    echo "--- 手動觸發更新 ---"
    mapfile -t projects < <(jq -r '.[].name' "$PROJECTS_FILE")
    if [ ${#projects[@]} -eq 0 ]; then
        echo "目前沒有任何專案可供更新。"
        read -n 1 -s -r -p "按任意鍵返回..."
        return 0
    fi
    echo "請選擇要更新的專案編號："
    for i in "${!projects[@]}"; do
        echo "  [$((i + 1))] ${projects[$i]}"
    done
    echo "  [q] 取消並返回"
    echo "-----------------------------------------"
    local choice
    read -r -p "請輸入您的選擇: " choice
    if [[ "$choice" =~ ^[qQ]$ ]]; then return 0; fi
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#projects[@]} )); then
        abort_with_msg "輸入無效。" || return
    fi
    local index=$((choice - 1))
    local name="${projects[$index]}"
    
    local path
    path=$(jq -r --arg n "$name" '.[] | select(.name == $n) | .path' "$PROJECTS_FILE")
    local md_file
    md_file=$(jq -r --arg n "$name" '.[] | select(.name == $n) | .md_file' "$PROJECTS_FILE")

    # 【關鍵】在呼叫 run_update 前，對路徑進行淨化
    local normalized_path
    normalized_path=$(python3 "$PATH_SCRIPT_PATH" validate "$path" |& tail -n 1)
    local normalized_md_file
    normalized_md_file=$(python3 "$PATH_SCRIPT_PATH" validate "$md_file" |& tail -n 1)

    run_update "$normalized_path" "$normalized_md_file"
    read -n 1 -s -r -p "按任意鍵返回主菜單..."
}



list_projects() {
    clear
    echo "--- 所有已註冊的專案列表 ---"
    local output
    output=$(jq -r '.[] | "名稱:\t\(.name)\n監控:\t\(.path)\n輸出:\t\(.md_file)\n-----------------------------------------"' "$PROJECTS_FILE")
    if [ -z "$output" ]; then
        echo "目前沒有任何已註冊的專案。"
    else
        echo -e "$output"
    fi
}

add_project() {
    clear; echo "--- 新增專案 ---"; echo "提示：請確保您輸入的路徑對應的檔案或目錄已存在。"
    local project_name project_path md_file_path
    read -r -p "請輸入專案別名: " project_name
    read -r -p "請輸入要監控的專案目錄路徑: " project_path
    read -r -p "請輸入要更新的 Markdown 檔案路徑: " md_file_path
    if [[ -z "$project_name" || -z "$project_path" || -z "$md_file_path" ]]; then abort_with_msg "所有欄位均不能為空。" || return; fi
    if ! python3 "$PATH_SCRIPT_PATH" validate "$project_path" "$md_file_path"; then abort_with_msg "路徑驗證失敗。" || return; fi
    if jq -e --arg n "$project_name" '.[] | select(.name == $n)' "$PROJECTS_FILE" > /dev/null; then abort_with_msg "專案別名已存在。" || return; fi
    local updated_json

# 【核心修正】先在 Shell 中生成 UUID，再通過 --arg 安全傳入，避免引號混亂
local new_uuid
new_uuid=$(uuidgen)
updated_json=$(jq --arg uuid "$new_uuid" --arg name "$project_name" --arg path "$project_path" --arg mdfile "$md_file_path" '. + [{uuid: $uuid, name: $name, path: $path, md_file: $mdfile}]' "$PROJECTS_FILE")
    
    echo "$updated_json" > "$PROJECTS_FILE"
    echo -e "\n✅ 成功新增專案！"; read -n 1 -s -r -p "按任意鍵繼續..."
}

edit_project() {
    clear; echo "--- 修改專案 ---"
    mapfile -t projects < <(jq -r '.[].name' "$PROJECTS_FILE")
    if [ ${#projects[@]} -eq 0 ]; then echo "沒有專案可修改。"; read -n 1 -s -r -p "按任意鍵返回..."; return 0; fi
    echo "請選擇要修改的專案編號："; for i in "${!projects[@]}"; do echo "  [$((i + 1))] ${projects[$i]}"; done; echo "  [q] 取消";
    local choice; read -r -p "請輸入您的選擇: " choice
    if [[ "$choice" =~ ^[qQ]$ ]]; then return 0; fi
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#projects[@]} )); then abort_with_msg "輸入無效。" || return; fi
    local index=$((choice - 1)); local name_to_edit="${projects[$index]}"
    clear; echo "--- 正在修改專案: $name_to_edit ---"; echo "提示：請直接按 Enter 以保留原值。"
    local old_path new_path old_md_file new_md_file
    old_path=$(jq -r --arg n "$name_to_edit" '.[] | select(.name == $n) | .path' "$PROJECTS_FILE")
    old_md_file=$(jq -r --arg n "$name_to_edit" '.[] | select(.name == $n) | .md_file' "$PROJECTS_FILE")
    read -r -p "新的專案路徑 (原: $old_path): " new_path
    read -r -p "新的 Markdown 檔案路徑 (原: $old_md_file): " new_md_file
    [ -z "$new_path" ] && new_path=$old_path
    [ -z "$new_md_file" ] && new_md_file=$old_md_file
    if ! python3 "$PATH_SCRIPT_PATH" validate "$new_path" "$new_md_file"; then abort_with_msg "路徑驗證失敗。" || return; fi
    local updated_json
    updated_json=$(jq --arg name "$name_to_edit" --arg path "$new_path" --arg mdfile "$new_md_file" '(map(if .name == $name then .path = $path | .md_file = $mdfile else . end))' "$PROJECTS_FILE")
    echo "$updated_json" > "$PROJECTS_FILE"
    echo -e "\n✅ 成功修改專案！"; read -n 1 -s -r -p "按任意鍵繼續..."
}

delete_project() {
    clear; echo "--- 刪除專案 ---"
    mapfile -t projects < <(jq -r '.[].name' "$PROJECTS_FILE")
    if [ ${#projects[@]} -eq 0 ]; then echo "沒有專案可刪除。"; read -n 1 -s -r -p "按任意鍵返回..."; return 0; fi
    echo "請選擇要刪除的專案編號："; for i in "${!projects[@]}"; do echo "  [$((i + 1))] ${projects[$i]}"; done; echo "  [q] 取消";
    local choice; read -r -p "請輸入您的選擇: " choice
    if [[ "$choice" =~ ^[qQ]$ ]]; then return 0; fi
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#projects[@]} )); then abort_with_msg "輸入無效。" || return; fi
    local index=$((choice - 1)); local name_to_delete="${projects[$index]}"
    echo -e "\n⚠️  您確定要刪除專案「${name_to_delete}」嗎？"; read -r -p "請輸入 'y' 或 'yes' 確認: " conf
    if ! [[ "$conf" =~ ^[yY]([eE][sS])?$ ]]; then echo "操作已取消。"; read -n 1 -s -r -p "按任意鍵返回..."; return 0; fi
    local updated_json
    updated_json=$(jq --arg name "$name_to_delete" 'del(.[] | select(.name == $name))' "$PROJECTS_FILE")
    echo "$updated_json" > "$PROJECTS_FILE"
    echo -e "\n✅ 成功刪除專案！"; read -n 1 -s -r -p "按任意鍵繼續..."
}


start_sentry() {
    set -x
    echo "--- 正在啟動哨兵 ---"
    # 讀取第一個專案的路徑 (在我們的測試中，只會有一個專案)
    # 我們使用 jq 來安全地讀取第一個專案的 .path 欄位
    local project_path
    project_path=$(jq -r '.[0].path' "$PROJECTS_FILE")

    # 如果沒有讀到任何專案路徑，就報錯並退出
    if [ -z "$project_path" ]; then
        abort_with_msg "專案設定檔中沒有找到任何專案。" || return
    fi

    echo "  > 正在為專案路徑啟動監控: ${project_path}"

# 【核心改造】啟用專屬日誌進行深度偵錯
local sentry_log_file="${LOGS_DIR}/sentry_debug.log"
echo "  > 哨兵偵錯日誌將記錄在: ${sentry_log_file}"
# 我們將標準輸出和標準錯誤都重定向到這個專屬日誌檔案
(inotifywait -m -r -e modify,create,delete,move --format '%w%f' "$project_path" > "$sentry_log_file" 2>&1 &)


stop_sentry() {
    echo "--- 正在停止哨兵 ---"
    echo "功能待實現..."
    read -n 1 -s -r -p "按任意鍵返回主菜單..."
}



# ==============================================================================
#  主執行區 (v4.0 智慧調度版)
# ==============================================================================

main_loop() {
    while true; do
        show_main_menu
        read -r choice
        case "$choice" in
            1) list_projects; read -n 1 -s -r -p "按任意鍵返回主菜單...";;
            2) add_project;;
            3) edit_project;;
            4) delete_project;;
            # 【新功能】為哨兵新增菜單選項
            5) start_sentry;;
            6) stop_sentry;;
            u|U) manual_update;;
            q|Q) echo "正在退出系統..."; break;;
            *) echo "無效的選擇，請重新輸入。"; sleep 1;;
        esac
    done
}

# 【核心改造】我們檢查傳給腳本的第一個參數 ($1)
# -z "$1" 的意思是，如果第一個參數是空的 (null or empty string)
if [ -z "${1-}" ]; then
    # 如果沒有提供任何參數，就跟以前一樣，啟動互動式主循環
    main_loop
else
    # 如果提供了參數 (例如 "start_sentry")，就直接把這個參數當作函式名來執行
    # "$@" 會把所有傳入的參數 (例如 start_sentry arg1 arg2) 都傳遞給要執行的函式
    "$1"
fi

