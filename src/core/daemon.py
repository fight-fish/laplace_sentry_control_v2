
# 我們需要的標準工具
import argparse
import json
import uuid
import os
import sys
import subprocess

# --- 【v3.1 終極導入修正】 ---
# 這段代碼解決了當 daemon.py 被 subprocess 直接執行時，無法找到兄弟模塊的問題。
# 它動態地將 src/ 目錄添加到 Python 的搜索路徑中。
if __name__ == '__main__' and __package__ is None:
    # 獲取當前腳本 (daemon.py) 的絕對路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 我們需要將 src/ 目錄（即 core/ 的上一級）加入到搜索路徑
    sys.path.insert(0, os.path.dirname(current_dir))
    # 現在，我們可以安全地使用絕對導入
    from core.path import normalize_path, validate_paths_exist
else:
    # 如果是作為模塊被導入（例如被 main.py 導入），則使用相對導入
    from .path import normalize_path, validate_paths_exist

# --- 全域專案根路徑設定 ---
# 讓 daemon 不論從哪裡被呼叫都能定位 src/ 與 shell/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if not os.path.exists(os.path.join(project_root, 'src')):
    raise RuntimeError(f"無法定位專案根目錄：{project_root}")


# --- 核心配置 ---
# 【v3.0 改造】適配測試環境。如果檢測到環境變數，就使用測試文件路徑。
# 這使得我們的 daemon 在被 unittest 調用時，能自動操作 mock 文件。
if 'TEST_PROJECTS_FILE' in os.environ:
    PROJECTS_FILE = os.environ['TEST_PROJECTS_FILE']
else:
    # 正常運行時的路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECTS_FILE = os.path.join(script_dir, '..', '..', 'data', 'projects.json')

# --- 輔助函式 ---
def read_projects_data():
    """一個通用的、健壯的讀取專案文件的輔助函式。"""
    try:
        # 【v3.0 改造】確保在文件不存在時，也能創建一個空的父目錄
        os.makedirs(os.path.dirname(PROJECTS_FILE), exist_ok=True)
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # 如果文件是空的或只包含空白字符，返回一個空列表
            if not content.strip():
                return []
            return json.loads(content)
    except FileNotFoundError:
        # 如果文件不存在，返回一個空列表
        return []
    except json.JSONDecodeError:
        # 如果文件內容不是有效的 JSON，返回一個錯誤並退出
        print(f"【守護進程致命錯誤】：專案文件 '{PROJECTS_FILE}' 內容損壞，不是有效的 JSON 格式。", file=sys.stderr)
        sys.exit(1)

def write_projects_data(data):
    """一個通用的、健壯的寫入專案文件的輔助函式。"""
    try:
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"【守護進程致命錯誤】：寫入專案文件 '{PROJECTS_FILE}' 時發生意外。\n  -> 原因：{e}", file=sys.stderr)
        sys.exit(1)

# 在 daemon.py 的 "輔助函式" 區域新增

def _get_targets_from_project(project_data):
    """
    【v3.3 兼容層】從單個專案記錄中，安全地獲取其目標文件列表。
    它能溫柔地處理各種歷史數據格式（字串、陣列、不存在），並永遠返回一個標準的陣列。
    """
    # 優先從面向未來的 'target_files' 欄位讀取
    targets = project_data.get('target_files')
    if isinstance(targets, list) and targets:
        return targets
    
    # 如果 'target_files' 沒有，再嘗試從兼容性的 'output_file' 讀取
    output = project_data.get('output_file')
    if isinstance(output, list) and output:
        return output
    
    # 最後，處理最糟糕的歷史遺留問題：'output_file' 是個非空字串
    if isinstance(output, str) and output.strip():
        return [output]
        
    # 如果都找不到，返回一個安全的空陣列
    return []


def handle_ping():
    """處理 PING 命令，打印 PONG 並成功退出。"""
    print("PONG")
    sys.exit(0)

def handle_list_projects():
    """處理 list_projects 命令，讀取 projects.json 並返回其內容。"""
    projects = read_projects_data()
    print(json.dumps(projects, indent=2, ensure_ascii=False))
    sys.exit(0)


# 在 daemon.py 中，替換舊的 handle_add_project 函式

def handle_add_project(args):
    """【v3.3 數據模型修正版】處理 add_project 命令，帶有八道審查關卡。"""
    # --- 審查邏輯保持不變 ---
    if len(args) != 3:
        print("【新增失敗】：參數數量不正確...", file=sys.stderr)
        sys.exit(1)
    name, path, output_file = args
    clean_path = normalize_path(path)
    clean_output_file = normalize_path(output_file)
    if not os.path.isabs(clean_path) or not os.path.isabs(clean_output_file):
        print("【新增失敗】：路徑格式錯誤...", file=sys.stderr)
        sys.exit(1)
    parent_dir = os.path.dirname(clean_output_file)
    if parent_dir and not os.path.isdir(parent_dir):
        print(f"【新增失敗】：目標文件所在資料夾不存在 -> {parent_dir}", file=sys.stderr)
        sys.exit(1)
    if not validate_paths_exist([clean_path]):
        print(f"【新增失敗】：專案目錄路徑不存在...", file=sys.stderr)
        sys.exit(1)
    projects = read_projects_data()
    if any(p['name'] == name for p in projects):
        print(f"【新增失敗】：專案別名 '{name}' 已被佔用...", file=sys.stderr)
        sys.exit(1)
    if any(normalize_path(p.get('path', '')) == clean_path for p in projects):
        print(f"【新增失敗】：專案路徑 '{clean_path}' 已被監控...", file=sys.stderr)
        sys.exit(1)
        
    # 【v3.3 修正】使用新的輔助函式進行重複性檢查，確保健壯性
    for p in projects:
        existing_targets = _get_targets_from_project(p)
        if any(normalize_path(target) == clean_output_file for target in existing_targets):
            print(f"【新增失敗】：目標文件 '{clean_output_file}' 已經被專案 '{p['name']}' 使用。", file=sys.stderr)
            sys.exit(1)

    # =================================================================
    # 【核心修正】採納「雙陣列」模型，確保寫入的數據模型絕對一致
    # =================================================================
    new_project = {
        "uuid": str(uuid.uuid4()),
        "name": name,
        "path": clean_path,
        "output_file": [clean_output_file],  # 兼容欄位，也使用陣列
        "target_files": [clean_output_file], # 未來權威欄位
    }
    # =================================================================

    projects.append(new_project)
    write_projects_data(projects)
    print("OK")
    sys.exit(0)


# 在 daemon.py 中，替換舊的 handle_edit_project 函式

def handle_edit_project(args):
    """【v3.3 數據模型修正版】處理 edit_project 命令。"""
    # --- 參數與 UUID 審查邏輯保持不變 ---
    if len(args) != 3:
        print("【編輯失敗】：參數數量不正確...", file=sys.stderr)
        sys.exit(1)
    uuid_to_edit, field, new_value = args
    allowed_fields = ['name', 'path', 'output_file']
    if field not in allowed_fields:
        print(f"【編輯失敗】：無效的欄位名稱。", file=sys.stderr)
        sys.exit(1)
    projects = read_projects_data()
    project_to_edit = next((p for p in projects if p['uuid'] == uuid_to_edit), None)
    if project_to_edit is None:
        print("【編輯失敗】：未找到具有該 UUID 的專案。", file=sys.stderr)
        sys.exit(1)
    other_projects = [p for p in projects if p['uuid'] != uuid_to_edit]

    # --- 根據不同欄位進行審查 ---
    if field == 'name':
        if any(p['name'] == new_value for p in other_projects):
            print("【編輯失敗】：新的專案別名已被佔用。", file=sys.stderr)
            sys.exit(1)
        project_to_edit['name'] = new_value
        
    elif field == 'path':
        clean_new_path = normalize_path(new_value)
        if not os.path.isabs(clean_new_path):
            print("【編輯失敗】：新的路徑必須是絕對路徑。", file=sys.stderr)
            sys.exit(1)
        if any(normalize_path(p.get('path', '')) == clean_new_path for p in other_projects):
            print("【編輯失敗】：新的專案路徑已被其他專案監控。", file=sys.stderr)
            sys.exit(1)
        if not validate_paths_exist([clean_new_path]):
            print("【編輯失敗】：新的路徑不存在或無效。", file=sys.stderr)
            sys.exit(1)
        project_to_edit['path'] = clean_new_path

    elif field == 'output_file':
        clean_new_output_file = normalize_path(new_value)
        if not os.path.isabs(clean_new_output_file):
            print("【編輯失敗】：新的目標文件路徑必須是絕對路徑。", file=sys.stderr)
            sys.exit(1)
            
        # 【v3.3 修正】使用新的輔助函式進行重複性檢查，確保健壯性
        for p in other_projects:
            existing_targets = _get_targets_from_project(p)
            if any(normalize_path(target) == clean_new_output_file for target in existing_targets):
                print(f"【編輯失敗】：目標文件 '{clean_new_output_file}' 已經被專案 '{p['name']}' 使用。", file=sys.stderr)
                sys.exit(1)

        # =================================================================
        # 【核心修正】採納「雙陣列」模型，統一更新兩個欄位
        # =================================================================
        project_to_edit['output_file'] = [clean_new_output_file]
        project_to_edit['target_files'] = [clean_new_output_file]
        # =================================================================

    write_projects_data(projects)
    print("OK")
    sys.exit(0)

def handle_delete_project(args):
    """【v3.0 新增】處理 delete_project 命令。"""
    # 第一關：參數數量審查
    if len(args) != 1:
        print("【刪除失敗】：參數數量不正確，需要 1 個參數 (uuid)。", file=sys.stderr)
        sys.exit(1)
        
    uuid_to_delete = args[0]
    projects = read_projects_data()
    
    # 過濾掉要刪除的專案，生成一個新列表
    new_projects = [p for p in projects if p['uuid'] != uuid_to_delete]
    
    # 第二關：UUID 存在性審查 (通過比較前後列表長度)
    if len(new_projects) == len(projects):
        print("【刪除失敗】：未找到具有該 UUID 的專案。", file=sys.stderr)
        sys.exit(1)

    # --- 【風險預留】 ---
    # TODO: 在此處檢查並停止與 uuid_to_delete 關聯的哨兵進程。
    # 確保在確認刪除前，哨兵已經被終止。

    # 最終關卡：寫入數據庫
    write_projects_data(new_projects)
    
    print("OK")
    sys.exit(0)


def handle_manual_update(args):
    """【v3.9 止血版】嚴格檢查 returncode，杜絕靜默失敗。"""
    if len(args) != 1:
        print("【手動更新失敗】：參數數量不正確，需要 1 個參數 (uuid)。", file=sys.stderr)
        sys.exit(1)

    uuid_to_update = args[0]

    # 1) 讀取名單並找到對應專案
    projects = read_projects_data()
    selected_project = next((p for p in projects if p.get('uuid') == uuid_to_update), None)
    if not selected_project:
        print(f"【手動更新失敗】：未找到具有該 UUID 的專案 '{uuid_to_update}'。", file=sys.stderr)
        sys.exit(1)

    # 2) 抓專案目錄
    project_path = selected_project.get('path')

    # 3) 取得第一個有效的目標檔（兼容 target_files(list) / output_file(list/str)）
    targets = _get_targets_from_project(selected_project)  # list
    target_doc_path = targets[0] if targets else None
    if not isinstance(target_doc_path, str) or not target_doc_path.strip():
        print(f"【手動更新失敗】：專案 '{selected_project.get('name','<未命名>')}' 沒有有效的目標文件。", file=sys.stderr)
        sys.exit(1)

    # ---- 訊息顯示 ----
    print(f"--- [工人] 開始執行更新 (由 daemon 調度) ---", file=sys.stderr)
    print(f"  - 監控目標: {project_path}", file=sys.stderr)
    print(f"  - 輸出文件: {target_doc_path}", file=sys.stderr)

    # 4) 調用 path.py 讀取舊內容
    path_script_path = os.path.join(project_root, 'src', 'core', 'path.py')
    try:
        read_process = subprocess.run(
            [sys.executable, path_script_path, 'read', target_doc_path],
            capture_output=True, text=True, encoding='utf-8', check=False
        )
        if read_process.returncode != 0:
            print(f"【手動更新失敗】：讀取目標文件失敗。\n{read_process.stderr}", file=sys.stderr)
            sys.exit(1)
        old_content = read_process.stdout
    except Exception as e:
        print(f"【手動更新失敗】：在調用路徑專家 (path.py) 時發生致命錯誤。\n  -> {e}", file=sys.stderr)
        sys.exit(1)

    # 5) 調用 worker.sh 執行核心更新
    worker_script_path = os.path.join(project_root, 'src', 'shell', 'worker.sh')
    try:
        worker_process = subprocess.run(
            ['bash', worker_script_path, project_path, target_doc_path],
            input=old_content,
            capture_output=True, text=True, encoding='utf-8',
            env=os.environ, check=False
        )
        if worker_process.stdout:
            print(worker_process.stdout, file=sys.stderr)
        if worker_process.stderr:
            print(worker_process.stderr, file=sys.stderr)
        if worker_process.returncode != 0:
            print("【手動更新失敗】：工人腳本 (worker.sh) 執行失敗，返回非零退出碼。", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"【手動更新失敗】：在調用工人腳本 (worker.sh) 時發生致命錯誤。\n  -> {e}", file=sys.stderr)
        sys.exit(1)

    # 6) 成功
    sys.exit(0)


def handle_manual_direct(args):
    """【v4.0 精簡版】自由手動更新：僅需輸入專案目錄與目標檔案。"""
    if len(args) != 2:
        print("【手動更新失敗】：需要 2 個參數 (project_path, target_doc_path)。", file=sys.stderr)
        sys.exit(1)

    project_path, target_doc_path = map(normalize_path, args)

    # 檢查專案路徑存在性（目標檔案由 path.py 自行檢查）
    if not os.path.exists(project_path):
        print(f"【手動更新失敗】：專案目錄不存在 -> {project_path}", file=sys.stderr)
        sys.exit(1)

    print(f"--- [工人] 開始執行自由手動更新 ---", file=sys.stderr)
    print(f"  - 專案目錄: {project_path}", file=sys.stderr)
    print(f"  - 目標文件: {target_doc_path}", file=sys.stderr)

    # --- 1. 調用 path.py 讀取目標檔案內容（舊內容） ---
    path_script_path = os.path.join(project_root, 'src', 'core', 'path.py')
    read_process = subprocess.run(
        [sys.executable, path_script_path, 'read', target_doc_path],
        capture_output=True, text=True, encoding='utf-8'
    )

    if read_process.returncode != 0:
        print(f"【手動更新失敗】：讀取目標文件失敗。\n{read_process.stderr}", file=sys.stderr)
        sys.exit(1)

    old_content = read_process.stdout

    # --- 2. 調用 worker.sh 寫入目標 ---
    worker_script_path = os.path.join(project_root, 'src', 'shell', 'worker.sh')
    worker_process = subprocess.run(
        ['bash', worker_script_path, project_path, target_doc_path],
        input=old_content, capture_output=True, text=True, encoding='utf-8', env=os.environ
    )

    if worker_process.stdout:
        print(worker_process.stdout, file=sys.stderr)
    if worker_process.stderr:
        print(worker_process.stderr, file=sys.stderr)
    if worker_process.returncode != 0:
        print(f"【手動更新失敗】：工人腳本執行錯誤。", file=sys.stderr)
        sys.exit(1)

    print("【自由手動更新成功】：已完成所有步驟。")
    sys.exit(0)



def main():
    """主執行區：【v3.0 C/S 架構服務器端】"""
    parser = argparse.ArgumentParser(description="後台守護進程：C/S 架構的服務器端。")
    subparsers = parser.add_subparsers(dest='command', help='可執行的命令', required=True)

    # 註冊所有指令
    subparsers.add_parser('ping', help='檢測與服務器的連接是否暢通。')
    subparsers.add_parser('list_projects', help='獲取所有已註冊專案的列表。')
    
    parser_add = subparsers.add_parser('add_project', help='新增一個專案。')
    parser_add.add_argument('params', nargs='*', help='name, path, output_file')

    parser_edit = subparsers.add_parser('edit_project', help='修改一個現有專案。')
    parser_edit.add_argument('params', nargs='*', help='uuid, field, new_value')

    parser_delete = subparsers.add_parser('delete_project', help='刪除一個現有專案。')
    parser_delete.add_argument('params', nargs='*', help='uuid')

    parser_update = subparsers.add_parser('manual_update', help='手動觸發一次更新。')
    parser_update.add_argument('params', nargs='*', help='uuid')

    parser_direct = subparsers.add_parser('manual_direct', help='以自由輸入兩參數方式執行更新。')
    parser_direct.add_argument('params', nargs='*', help='project_path, target_doc_path')

    args = parser.parse_args(sys.argv[1:])

    # 根據指令分派到對應的處理函式
    if args.command == 'ping':
        handle_ping()
    elif args.command == 'list_projects':
        handle_list_projects()
    elif args.command == 'add_project':
        handle_add_project(args.params)
    elif args.command == 'edit_project':
        handle_edit_project(args.params)
    elif args.command == 'delete_project':
        handle_delete_project(args.params)
    elif args.command == 'manual_direct':
        handle_manual_direct(args.params)
    elif args.command == 'manual_update':
        handle_manual_update(args.params)

    else:
        # 雖然 argparse 的 required=True 讓這裡幾乎不可能到達，但作為防禦性編程保留
        print(f"【守護進程錯誤】：收到未知或未處理的命令 '{args.command}'", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
