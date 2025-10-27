#!/bin/bash
# Laplace Sentry Control - 管理專家
# 版本: 4.1 (鳳凰涅槃版)

# --- 嚴格模式與全域變數 ---
set -euo pipefail
trap 'echo "【管理專家錯誤】: 錯誤發生在 ${BASH_SOURCE[0]} 的第 ${LINENO} 行" >&2' ERR

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PATH_SCRIPT_PATH="${SCRIPT_DIR}/../core/path.py"
LOGS_DIR="${SCRIPT_DIR}/../../logs"
PROJECTS_FILE="${SCRIPT_DIR}/../../data/projects.json"

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
    echo "   通用目錄哨兵 - 控制中心 v4.1"
    echo "========================================"
    echo "  [1] 列出所有專案"
    echo "  [2] 新增一個專案"
    echo "  [3] 修改一個專案"
    echo "  [4] 刪除一個專案"
    echo "  [5] 啟動哨兵"
    echo "  [6] 停止哨兵"
    echo "----------------------------------------"
    echo "  [u] 手動觸發一次更新..."
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

################################################################################
#  【核心調試資產：手動更新模式】 - 永久保留，嚴禁刪除
################################################################################
#
#  【歷史教訓與設計原則】
#  本區塊中的 `run_update` 與 `manual_update` 函式，是我們在經歷了
#  【階段零】史詩級除錯戰役後，沉澱下來的最寶貴的「核心調試資產」。
#
#  它們存在的唯一目的，是提供一個完全獨立於「背景哨兵」的、可
#  在「前台」手動執行的、透明的、可預測的更新通道。
#
#  歷史已經反覆證明：當背景的 `inotifywait` 哨兵出現任何無法解釋
#  的「靜默罷工」或詭異行為時，【手動模式】是我們繞開所有迷霧、
#  直面問題核心、驗證核心工作流（從 `worker.sh` 到所有專家）是否
#  正常的、唯一的、最終的真理來源。
#
#  【維護憲法】
#  任何時候，對本專案的任何重構，都絕對不能以任何理由，刪除或
#  破壞此「手動更新模式」。其在主菜單中的 `[u]` 選項，必須被永
#  久保留。
#
#  —— 本原則由專案所有者帕爾，於史詩級除錯戰役後，親自確立。
#
################################################################################
run_update() {
    local project_path=$1
    local target_doc_path=$2
    echo "--- 開始執行手動更新 ---"
    echo "  - 監控目標: ${project_path}"
    echo "  - 輸出文件: ${target_doc_path}"

    # 【核心改造】我們不再自己幹活，而是像哨兵一樣，呼叫工人來幹活
    local worker_script_path
    worker_script_path=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)/worker.sh

    # 1. 像哨兵一樣，先讀取舊文件內容
    local old_content
    old_content=$(python3 "$PATH_SCRIPT_PATH" read "$target_doc_path" 2>/dev/null || true)
    
    # 2. 像哨兵一樣，將讀取到的內容通過管道，交給工人去處理
    if echo "$old_content" | bash "$worker_script_path" "$project_path" "$target_doc_path"; then
        echo "✅ 更新成功完成！"
        return 0
    else
        # 這裡我們不使用 abort_with_msg，因為工人已經打印了詳細的錯誤日誌
        echo -e "\n❌ \e[31m錯誤: 手動更新失敗，請檢查上方由工人報告的錯誤信息。\e[0m" >&2
        return 1
    fi
}

# 在 src/shell/control.sh 中

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
    
    # 【終極撥亂反正】
    # 我們必須像 start_sentry 一樣，在傳遞之前，對路徑進行權威的淨化！
    local raw_project_path
    raw_project_path=$(jq -r --arg n "$name" '.[] | select(.name == $n) | .path' "$PROJECTS_FILE")
    local raw_md_file_path
    raw_md_file_path=$(jq -r --arg n "$name" '.[] | select(.name == $n) | .md_file' "$PROJECTS_FILE")

    # 調用 path.py 的 normalize 命令，得到乾淨的、Linux 風格的絕對路徑
    local normalized_project_path
    normalized_project_path=$(python3 "$PATH_SCRIPT_PATH" normalize "$raw_project_path")
    local normalized_md_file_path
    normalized_md_file_path=$(python3 "$PATH_SCRIPT_PATH" normalize "$raw_md_file_path")

    # 將【淨化後】的路徑，傳遞給 run_update
    run_update "$normalized_project_path" "$normalized_md_file_path"
    
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
    if ! python3 "$PATH_SCRIPT_PATH" validate "$project_path"; then abort_with_msg "專案目錄路徑驗證失敗。" || return; fi
    if jq -e --arg n "$project_name" '.[] | select(.name == $n)' "$PROJECTS_FILE" > /dev/null; then abort_with_msg "專案別名已存在。" || return; fi
    local new_uuid; new_uuid=$(uuidgen)
    local updated_json; updated_json=$(jq --arg uuid "$new_uuid" --arg name "$project_name" --arg path "$project_path" --arg mdfile "$md_file_path" '. + [{uuid: $uuid, name: $name, path: $path, md_file: $mdfile}]' "$PROJECTS_FILE")
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
    
    # 【安全機制】修改前先停止哨兵
    if [ -f "/tmp/sentry_${name_to_edit}.pid" ]; then
        echo "⚠️ 檢測到專案正在運行，將自動為您停止哨兵..."
        stop_sentry_by_name "$name_to_edit"
        sleep 1
    fi

    clear; echo "--- 正在修改專案: $name_to_edit ---"; echo "提示：請直接按 Enter 以保留原值。"
    local old_path new_path old_md_file new_md_file
    old_path=$(jq -r --arg n "$name_to_edit" '.[] | select(.name == $n) | .path' "$PROJECTS_FILE")
    old_md_file=$(jq -r --arg n "$name_to_edit" '.[] | select(.name == $n) | .md_file' "$PROJECTS_FILE")
    read -r -p "新的專案路徑 (原: $old_path): " new_path
    read -r -p "新的 Markdown 檔案路徑 (原: $old_md_file): " new_md_file
    [ -z "$new_path" ] && new_path=$old_path
    [ -z "$new_md_file" ] && new_md_file=$old_md_file
    if ! python3 "$PATH_SCRIPT_PATH" validate "$new_path"; then abort_with_msg "新的專案目錄路徑驗證失敗。" || return; fi
    local updated_json; updated_json=$(jq --arg name "$name_to_edit" --arg path "$new_path" --arg mdfile "$new_md_file" '(map(if .name == $name then .path = $path | .md_file = $mdfile else . end))' "$PROJECTS_FILE")
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

    # 【安全機制】刪除前先停止哨兵
    if [ -f "/tmp/sentry_${name_to_delete}.pid" ]; then
        echo "⚠️ 檢測到專案正在運行，將自動為您停止哨兵..."
        stop_sentry_by_name "$name_to_delete"
        sleep 1
    fi

    echo -e "\n⚠️  您確定要刪除專案「${name_to_delete}」嗎？"; read -r -p "請輸入 'y' 或 'yes' 確認: " conf
    if ! [[ "$conf" =~ ^[yY]([eE][sS])?$ ]]; then echo "操作已取消。"; read -n 1 -s -r -p "按任意鍵返回..."; return 0; fi
    local updated_json; updated_json=$(jq --arg name "$name_to_delete" 'del(.[] | select(.name == $name))' "$PROJECTS_FILE")
    echo "$updated_json" > "$PROJECTS_FILE"
    echo -e "\n✅ 成功刪除專案！"; read -n 1 -s -r -p "按任意鍵繼續..."
}

# 內部函式，供其他函式調用
stop_sentry_by_name() {
    local name=$1
    local pid_file="/tmp/sentry_${name}.pid"
    if [ ! -f "$pid_file" ]; then
        echo "  > 專案 '${name}' 的哨兵並未運行。"
        return 0
    fi
    local pid_to_kill; pid_to_kill=$(cat "$pid_file")
    if ! [[ "$pid_to_kill" =~ ^[0-9]+$ ]]; then
        echo "  > 專案 '${name}' 的 PID 檔案內容無效。"
        rm -f "$pid_file"
        return 1
    fi
    echo "  > 正在停止 PID 為 ${pid_to_kill} 的哨兵進程..."
    if kill "$pid_to_kill" 2>/dev/null; then
        echo "  > 成功發送停止信號。"
    else
        echo "  > 哨兵進程 (PID: ${pid_to_kill}) 已不存在。"
    fi
    rm -f "$pid_file"
    echo "  > 專案 '${name}' 的哨兵已停止。"
}


start_sentry() {
    clear; echo "--- 啟動哨兵 ---"
    mapfile -t projects < <(jq -r '.[].name' "$PROJECTS_FILE")
    if [ ${#projects[@]} -eq 0 ]; then echo "沒有專案可供啟動哨兵。"; read -n 1 -s -r -p "按任意鍵返回..."; return 0; fi
    echo "請選擇要啟動哨兵的專案編號："; for i in "${!projects[@]}"; do echo "  [$((i + 1))] ${projects[$i]}"; done; echo "  [q] 取消";
    local choice; read -r -p "請輸入您的選擇: " choice
    if [[ "$choice" =~ ^[qQ]$ ]]; then return 0; fi
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#projects[@]} )); then abort_with_msg "輸入無效。" || return; fi
    local index=$((choice - 1)); local name="${projects[$index]}"
    local project_json; project_json=$(jq -r --arg n "$name" '.[] | select(.name == $n)' "$PROJECTS_FILE")
    
    local raw_project_path; raw_project_path=$(echo "$project_json" | jq -r '.path')
    local raw_md_file_path; raw_md_file_path=$(echo "$project_json" | jq -r '.md_file')
    local normalized_project_path; normalized_project_path=$(python3 "$PATH_SCRIPT_PATH" normalize "$raw_project_path")
    local normalized_md_file_path; normalized_md_file_path=$(python3 "$PATH_SCRIPT_PATH" normalize "$raw_md_file_path")

    local pid_file="/tmp/sentry_${name}.pid"
    if [ -f "$pid_file" ]; then abort_with_msg "專案 '$name' 的哨兵似乎已在運行中。請先停止它。" || return; fi

    echo "  > 正在為專案 '${name}' 啟動監控: ${normalized_project_path}"
    
    (
        local worker_script_path; worker_script_path=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)/worker.sh
        
        # 【v4.1 核心邏輯】
        # 移除與 -m 衝突的 -r 參數，並在循環內部處理數據傳遞
        inotifywait -m -q -e modify,create,delete,move "$normalized_project_path" | while read -r event; do
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 監測到事件 ($event)，正在呼叫工人..."
            
            # 在調用工人前，先讀取最新的舊文件內容
            local old_content
            old_content=$(python3 "$PATH_SCRIPT_PATH" read "$normalized_md_file_path" 2>/dev/null || true)
            
            # 將最新的舊文件內容，通過管道傳遞給工人
            echo "$old_content" | bash "$worker_script_path" "$normalized_project_path" "$normalized_md_file_path"
        done
    ) > "${LOGS_DIR}/sentry_${name}.log" 2>&1 &

    local inotify_pid=$!
    echo "$inotify_pid" > "$pid_file"
    
    echo "✅ 專案 '${name}' 的哨兵已啟動，PID 為: ${inotify_pid}"
    read -n 1 -s -r -p "按任意鍵返回主菜單..."
}

stop_sentry() {
    clear; echo "--- 停止哨兵 ---"
    mapfile -t projects < <(jq -r '.[].name' "$PROJECTS_FILE")
    if [ ${#projects[@]} -eq 0 ]; then echo "沒有專案可停止。"; read -n 1 -s -r -p "按任意鍵返回..."; return 0; fi
    echo "請選擇要停止哨兵的專案編號："; for i in "${!projects[@]}"; do echo "  [$((i + 1))] ${projects[$i]}"; done; echo "  [q] 取消";
    local choice; read -r -p "請輸入您的選擇: " choice
    if [[ "$choice" =~ ^[qQ]$ ]]; then return 0; fi
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#projects[@]} )); then abort_with_msg "輸入無效。" || return; fi
    local index=$((choice - 1)); local name_to_stop="${projects[$index]}"
    stop_sentry_by_name "$name_to_stop"
    read -n 1 -s -r -p "按任意鍵返回主菜單..."
}

# ==============================================================================
#  主執行區
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
            5) start_sentry;;
            6) stop_sentry;;
            u|U) manual_update;;
            q|Q) echo "正在退出系統..."; break;;
            *) echo "無效的選擇，請重新輸入。"; sleep 1;;
        esac
    done
}

# 如果沒有傳入參數，就運行主循環；否則，執行傳入的函式名
if [ -z "${1-}" ]; then
    main_loop
else
    "$1"
fi
