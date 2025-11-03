# src/core/daemon.py

# 我們需要導入（import）幾個 Python 內建的標準工具：
import argparse     # 用於創建專業的命令列介面。
import json         # 用於讀寫 JSON 格式的數據。
import uuid         # 用於生成獨一無二的專案 ID。
import os           # 用於與作業系統互動，如處理路徑。
import sys          # 用於讀取系統參數和控制腳本退出。
import subprocess   # 用於調用外部腳本，如 worker.sh。

# --- 【v3.1 終極導入修正】 ---
# HACK: 這段代碼是我們在日誌 031 中，為了解決 `subprocess` 直接執行此文件時，
# 無法找到兄弟模塊（如 path.py）而導致的「靜默崩潰」問題的最終解決方案。
if __name__ == '__main__' and __package__ is None:
    # 我們獲取當前腳本 (daemon.py) 的絕對路徑。
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 然後，我們將其父目錄的父目錄（即專案根目錄）添加到 Python 的搜索路徑列表的最前面。
    sys.path.insert(0, os.path.dirname(os.path.dirname(current_dir)))
    # 現在，我們可以安全地使用從 `src` 開始的絕對導入路徑了。
    from src.core.path import normalize_path, validate_paths_exist
else:
    # 如果這個文件是作為一個模組被其他 Python 腳本（如 main.py）導入的，
    # 我們就使用標準的相對導入語法。
    from .path import normalize_path, validate_paths_exist

# --- 全域配置 (Global Configuration) ---

# 我們計算出專案的根目錄，這樣無論從哪裡調用 daemon，它都能準確地定位到其他文件。
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# DEFENSE: 啟動時自我檢查，如果連 src 目錄都找不到，說明環境有問題，立刻報錯退出。
if not os.path.exists(os.path.join(project_root, 'src')):
    raise RuntimeError(f"無法定位專案根目錄：{project_root}")

# HACK: 這裡我們通過檢查環境變數，來實現「測試環境」和「生產環境」的數據文件分離。
# 這使得我們的自動化單元測試（unittest）可以在不污染生產數據的情況下運行。
if 'TEST_PROJECTS_FILE' in os.environ:
    PROJECTS_FILE = os.environ['TEST_PROJECTS_FILE']
else:
    # 正常運行時，使用 data/ 目錄下的標準數據文件。
    PROJECTS_FILE = os.path.join(project_root, 'data', 'projects.json')

# --- 數據庫輔助函式 (Database Helper Functions) ---

def read_projects_data():
    """一個通用的、健壯的讀取專案數據文件的輔助函式。"""
    try:
        # DEFENSE: 在讀取前，先確保目標目錄存在，如果不存在就創建它。
        os.makedirs(os.path.dirname(PROJECTS_FILE), exist_ok=True)
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # DEFENSE: 如果文件是空的或只包含空白字符，返回一個安全的空列表。
            if not content.strip():
                return []
            return json.loads(content)
    except FileNotFoundError:
        # 如果文件本身不存在，也返回一個安全的空列表。
        return []
    except json.JSONDecodeError:
        # 如果文件內容不是有效的 JSON，這是一個嚴重問題，必須報錯並中止程式。
        print(f"【守護進程致命錯誤】：專案文件 '{PROJECTS_FILE}' 內容損壞，不是有效的 JSON 格式。", file=sys.stderr)
        sys.exit(1)

def write_projects_data(data):
    """一個通用的、健壯的寫入專案數據文件的輔助函式。"""
    try:
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
            # 我們使用 indent=2 來讓 JSON 文件格式化，方便人類閱讀。
            # ensure_ascii=False 確保中文字符能被正確寫入，而不是被轉義。
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"【守護進程致命錯誤】：寫入專案文件 '{PROJECTS_FILE}' 時發生意外。\n  -> 原因：{e}", file=sys.stderr)
        sys.exit(1)

def _get_targets_from_project(project_data):
    """
    【v3.3 兼容層】從單個專案記錄中，安全地獲取其目標文件列表。
    COMPAT: 這是為了溫柔地處理各種歷史數據格式（字串、陣列、不存在），並永遠返回一個標準的陣列。
    它體現了我們在日誌 036 中確立的「向後兼容」原則。
    """
    # 1. 優先從面向未來的 'target_files' 欄位讀取。
    targets = project_data.get('target_files')
    if isinstance(targets, list) and targets:
        return targets

    # 2. 如果沒有，再嘗試從兼容性的 'output_file' 讀取。
    output = project_data.get('output_file')
    if isinstance(output, list) and output:
        return output

    # 3. 最後，處理最糟糕的歷史遺留問題：'output_file' 是個非空字串。
    if isinstance(output, str) and output.strip():
        return [output]

    # 4. 如果都找不到，返回一個安全的空陣列，防止後續操作出錯。
    return []

# --- 命令處理函式 (Command Handlers) ---

def handle_ping():
    """處理 'ping' 命令，打印 'PONG' 並成功退出。"""
    print("PONG")
    sys.exit(0)

def handle_list_projects():
    """處理 'list_projects' 命令，讀取數據並以 JSON 格式打印到標準輸出。"""
    projects = read_projects_data()
    print(json.dumps(projects, indent=2, ensure_ascii=False))
    sys.exit(0)

def handle_add_project(args):
    """【v3.3 數據模型修正版】處理 'add_project' 命令，帶有八道審查關卡。"""
    # DEFENSE: 這是我們在日誌 029 和 035 中，通過壓力測試建立起來的防禦體系。
    # 關卡 1：參數數量審查
    if len(args) != 3:
        print("【新增失敗】：參數數量不正確，需要 3 個參數 (name, path, output_file)。", file=sys.stderr)
        sys.exit(1)
    name, path, output_file = args
    clean_path = normalize_path(path)
    clean_output_file = normalize_path(output_file)
    # 關卡 2：路徑格式審查（必須是絕對路徑）
    if not os.path.isabs(clean_path) or not os.path.isabs(clean_output_file):
        print("【新增失敗】：所有路徑都必須是絕對路徑。", file=sys.stderr)
        sys.exit(1)
    # 關卡 3：目標文件父目錄存在性審查
    parent_dir = os.path.dirname(clean_output_file)
    if parent_dir and not os.path.isdir(parent_dir):
        print(f"【新增失敗】：目標文件所在的資料夾不存在 -> {parent_dir}", file=sys.stderr)
        sys.exit(1)
    # 關卡 4：專案目錄存在性審查
    if not validate_paths_exist([clean_path]):
        print(f"【新增失敗】：專案目錄路徑不存在 -> {clean_path}", file=sys.stderr)
        sys.exit(1)
    projects = read_projects_data()
    # 關卡 5：專案別名唯一性審查
    if any(p['name'] == name for p in projects):
        print(f"【新增失敗】：專案別名 '{name}' 已被佔用。", file=sys.stderr)
        sys.exit(1)
    # 關卡 6：專案路徑唯一性審查
    if any(normalize_path(p.get('path', '')) == clean_path for p in projects):
        print(f"【新增失敗】：專案路徑 '{clean_path}' 已被其他專案監控。", file=sys.stderr)
        sys.exit(1)
    # 關卡 7：目標文件唯一性審查
    for p in projects:
        existing_targets = _get_targets_from_project(p)
        if any(normalize_path(target) == clean_output_file for target in existing_targets):
            print(f"【新增失敗】：目標文件 '{clean_output_file}' 已經被專案 '{p['name']}' 使用。", file=sys.stderr)
            sys.exit(1)

    # 【v3.3 核心修正】我們採納「雙陣列」模型，確保寫入的數據模型絕對一致和面向未來。
    new_project = {
        "uuid": str(uuid.uuid4()),
        "name": name,
        "path": clean_path,
        "output_file": [clean_output_file],  # COMPAT: 為了兼容舊邏輯，也使用陣列。
        "target_files": [clean_output_file], # FUTURE: 未來的權威欄位。
    }

    projects.append(new_project)
    write_projects_data(projects)
    print("OK")
    sys.exit(0)

def handle_edit_project(args):
    """【v3.3 數據模型修正版】處理 'edit_project' 命令。"""
    if len(args) != 3:
        print("【編輯失敗】：參數數量不正確...", file=sys.stderr)
        sys.exit(1)
    uuid_to_edit, field, new_value = args
    allowed_fields = ['name', 'path', 'output_file']
    if field not in allowed_fields:
        print(f"【編輯失敗】：無效的欄位名稱 '{field}'。", file=sys.stderr)
        sys.exit(1)
    projects = read_projects_data()
    project_to_edit = next((p for p in projects if p['uuid'] == uuid_to_edit), None)
    if project_to_edit is None:
        print("【編輯失敗】：未找到具有該 UUID 的專案。", file=sys.stderr)
        sys.exit(1)
    other_projects = [p for p in projects if p['uuid'] != uuid_to_edit]

    # DEFENSE: 根據不同欄位，執行不同的審查邏輯。
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
        for p in other_projects:
            existing_targets = _get_targets_from_project(p)
            if any(normalize_path(target) == clean_new_output_file for target in existing_targets):
                print(f"【編輯失敗】：目標文件 '{clean_new_output_file}' 已經被專案 '{p['name']}' 使用。", file=sys.stderr)
                sys.exit(1)
        # 【v3.3 核心修正】採納「雙陣列」模型，統一更新兩個欄位。
        project_to_edit['output_file'] = [clean_new_output_file]
        project_to_edit['target_files'] = [clean_new_output_file]

    write_projects_data(projects)
    print("OK")
    sys.exit(0)

def handle_delete_project(args):
    """處理 'delete_project' 命令。"""
    if len(args) != 1:
        print("【刪除失敗】：參數數量不正確，需要 1 個參數 (uuid)。", file=sys.stderr)
        sys.exit(1)
    uuid_to_delete = args[0]
    projects = read_projects_data()
    # 我們用「列表推導式」來過濾掉要刪除的專案，生成一個新列表。
    new_projects = [p for p in projects if p['uuid'] != uuid_to_delete]
    # DEFENSE: 通過比較前後列表長度，來判斷是否真的找到了要刪除的專案。
    if len(new_projects) == len(projects):
        print("【刪除失敗】：未找到具有該 UUID 的專案。", file=sys.stderr)
        sys.exit(1)
    
    # TODO: 在此處檢查並停止與 uuid_to_delete 關聯的哨兵進程。
    # 這是【任務 2.1】的核心部分，確保在刪除數據前，先停止正在運行的進程。

    write_projects_data(new_projects)
    print("OK")
    sys.exit(0)

def handle_manual_update(args):
    """
    【v3.9 止血版】處理 'manual_update' 命令，嚴格檢查每一步的返回碼。
    TODO: 這是「廢除 worker.sh」戰略決策下的過渡期產物。
    它的最終目標是將所有 subprocess 調用，都替換為純 Python 的內部函式調用。
    """
    if len(args) != 1:
        print("【手動更新失敗】：參數數量不正確，需要 1 個參數 (uuid)。", file=sys.stderr)
        sys.exit(1)
    uuid_to_update = args[0]
    projects = read_projects_data()
    selected_project = next((p for p in projects if p.get('uuid') == uuid_to_update), None)
    if not selected_project:
        print(f"【手動更新失敗】：未找到具有該 UUID 的專案 '{uuid_to_update}'。", file=sys.stderr)
        sys.exit(1)

    project_path = selected_project.get('path')
    # 我們使用「兼容層」來安全地獲取目標文件列表。
    targets = _get_targets_from_project(selected_project)
    target_doc_path = targets[0] if targets else None
    if not isinstance(target_doc_path, str) or not target_doc_path.strip():
        print(f"【手動更新失敗】：專案 '{selected_project.get('name','<未命名>')}' 沒有有效的目標文件。", file=sys.stderr)
        sys.exit(1)

    print(f"--- [守護進程] 正在調度手動更新 ---", file=sys.stderr)
    print(f"  - 專案目錄: {project_path}", file=sys.stderr)
    print(f"  - 目標文件: {target_doc_path}", file=sys.stderr)

    # HACK: 我們在這裡手動地、按順序地調用「路徑專家」和「工人腳本」。
    # 這是一個典型的、脆弱的跨語言調用鏈，是我們未來要消除的技術債。
    try:
        # 步驟 1: 調用 path.py 讀取舊內容
        path_script_path = os.path.join(project_root, 'src', 'core', 'path.py')
        read_process = subprocess.run(
            [sys.executable, path_script_path, 'read', target_doc_path],
            capture_output=True, text=True, encoding='utf-8', check=False
        )
        # DEFENSE: 嚴格檢查返回碼，杜絕靜默失敗。
        if read_process.returncode != 0:
            print(f"【手動更新失敗】：讀取目標文件失敗。\n{read_process.stderr}", file=sys.stderr)
            sys.exit(1)
        old_content = read_process.stdout

        # 步驟 2: 調用 worker.sh 執行核心更新
        worker_script_path = os.path.join(project_root, 'src', 'shell', 'worker.sh')
        worker_process = subprocess.run(
            ['bash', worker_script_path, project_path, target_doc_path],
            input=old_content,
            capture_output=True, text=True, encoding='utf-8',
            env=os.environ, check=False
        )
        if worker_process.stdout: print(worker_process.stdout, file=sys.stderr)
        if worker_process.stderr: print(worker_process.stderr, file=sys.stderr)
        if worker_process.returncode != 0:
            print("【手動更新失敗】：工人腳本 (worker.sh) 執行失敗。", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"【手動更新失敗】：在調用外部腳本時發生致命錯誤。\n  -> {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

def handle_manual_direct(args):
    """【v4.0 精簡版】處理 'manual_direct' 命令，一個純粹的調試工具。"""
    # TODO: 這個函式與 handle_manual_update 存在大量重複程式碼，未來應進行重構。
    if len(args) != 2:
        print("【手動更新失敗】：需要 2 個參數 (project_path, target_doc_path)。", file=sys.stderr)
        sys.exit(1)
    project_path, target_doc_path = map(normalize_path, args)
    if not os.path.exists(project_path):
        print(f"【手動更新失敗】：專案目錄不存在 -> {project_path}", file=sys.stderr)
        sys.exit(1)

    print(f"--- [守護進程] 正在調度自由手動更新 ---", file=sys.stderr)
    print(f"  - 專案目錄: {project_path}", file=sys.stderr)
    print(f"  - 目標文件: {target_doc_path}", file=sys.stderr)

    try:
        path_script_path = os.path.join(project_root, 'src', 'core', 'path.py')
        read_process = subprocess.run(
            [sys.executable, path_script_path, 'read', target_doc_path],
            capture_output=True, text=True, encoding='utf-8', check=False
        )
        if read_process.returncode != 0:
            print(f"【手動更新失敗】：讀取目標文件失敗。\n{read_process.stderr}", file=sys.stderr)
            sys.exit(1)
        old_content = read_process.stdout

        worker_script_path = os.path.join(project_root, 'src', 'shell', 'worker.sh')
        worker_process = subprocess.run(
            ['bash', worker_script_path, project_path, target_doc_path],
            input=old_content, capture_output=True, text=True, encoding='utf-8', env=os.environ, check=False
        )
        if worker_process.stdout: print(worker_process.stdout, file=sys.stderr)
        if worker_process.stderr: print(worker_process.stderr, file=sys.stderr)
        if worker_process.returncode != 0:
            print(f"【手動更新失敗】：工人腳本執行錯誤。", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"【手動更新失敗】：在調用外部腳本時發生致命錯誤。\n  -> {e}", file=sys.stderr)
        sys.exit(1)

    print("【自由手動更新成功】：已完成所有步驟。")
    sys.exit(0)

# --- 主執行區 (Main Execution) ---

def main():
    """主執行區：【v3.0 C/S 架構服務器端】的命令列介面。"""
    parser = argparse.ArgumentParser(description="後台守護進程：C/S 架構的服務器端。")
    subparsers = parser.add_subparsers(dest='command', help='可執行的命令', required=True)

    # 我們在這裡註冊所有 daemon 能理解的「動詞」。
    subparsers.add_parser('ping', help='檢測與服務器的連接是否暢通。')
    subparsers.add_parser('list_projects', help='獲取所有已註冊專案的列表。')
    parser_add = subparsers.add_parser('add_project', help='新增一個專案。')
    parser_add.add_argument('params', nargs='*', help='name, path, output_file')
    parser_edit = subparsers.add_parser('edit_project', help='修改一個現有專案。')
    parser_edit.add_argument('params', nargs='*', help='uuid, field, new_value')
    parser_delete = subparsers.add_parser('delete_project', help='刪除一個現有專案。')
    parser_delete.add_argument('params', nargs='*', help='uuid')
    parser_update = subparsers.add_parser('manual_update', help='依名單手動觸發一次更新。')
    parser_update.add_argument('params', nargs='*', help='uuid')
    parser_direct = subparsers.add_parser('manual_direct', help='以自由輸入方式執行更新。')
    parser_direct.add_argument('params', nargs='*', help='project_path, target_doc_path')

    # 解析從 sys.argv 傳入的參數。
    args = parser.parse_args(sys.argv[1:])

    # 根據解析出的命令，分派到對應的處理函式。
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
        # DEFENSE: 雖然 argparse 的 required=True 讓這裡幾乎不可能到達，但作為防禦性編程保留。
        print(f"【守護進程錯誤】：收到未知或未處理的命令 '{args.command}'", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
