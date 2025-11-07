# src/core/daemon.py

# 我們需要 導入（import）一系列 Python 內建的工具和我們自己的專家模塊。
import json
import uuid
import os
import sys
import time
from typing import Optional, Tuple, List, Dict, Any

# --- 【v4.0 依賴注入】 ---
# 我們現在只導入我們需要的、真正屬於「專家」的工具。
# 從我們自己的「路徑專家（path）」模塊中，導入（import）「正規化路徑」和「驗證路徑存在」這兩個函式。
from .path import normalize_path, validate_paths_exist
# 從我們自己的「工人專家（worker）」模塊中，導入（import）「執行更新工作流」這個函式。
from .worker import execute_update_workflow
# 【核心重構】我們導入全新的「I/O 網關」，它是我們所有文件操作的唯一安全出口。
from .io_gateway import safe_read_modify_write

# --- 全局配置 ---
# 我們計算出專案的根目錄路徑。
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# 我們用「if...in...」結構來判斷，如果（if）在「系統環境變數（os.environ）」這個大盒子裡，
# 存在一個名叫「TEST_PROJECTS_FILE」的標籤...
if 'TEST_PROJECTS_FILE' in os.environ:
    # ...我們就用這個標籤對應的值，作為我們專案列表文件的路徑。
    PROJECTS_FILE = os.environ['TEST_PROJECTS_FILE']
# 否則（else）...
else:
    # ...我們就使用正常的、生產環境下的文件路徑。
    PROJECTS_FILE = os.path.join(project_root, 'data', 'projects.json')

# --- 數據庫輔助函式 (現在由 I/O 網關代理) ---

# 我們用「def」來 定義（define）一個函式，名叫「read_projects_data」。
# 它的作用是讀取專案列表。
def read_projects_data() -> List[Dict[str, Any]]:
    # TAG: DECOUPLE (解耦)
    # 這個函式現在的職責非常單純：它將「讀取」這個具體任務，完全委託給了 I/O 網關。
    try:
        # 我們用「def」來 定義（define）一個什麼都不做的「回調函式」。
        # 因為我們只想讀取數據，不想做任何修改。
        def read_only_callback(data):
            # 它接收到數據後，直接將其原樣 返回（return）。
            return data
        
        # 我們調用「safe_read_modify_write」網關，並把「隻讀」的回調函式傳給它。
        # 網關會自動處理文件不存在或損壞的情況。
        return safe_read_modify_write(PROJECTS_FILE, read_only_callback, serializer='json')
    # 我們用「except IOError」來捕獲網關可能報告的任何 I/O 錯誤（如鎖失敗）。
    except IOError as e:
        # 如果出錯，我們就 打印（print）一條警告到「標準錯誤流（stderr）」。
        print(f"【守護進程警告】：讀取專案文件時出錯: {e}", file=sys.stderr)
        # 然後 返回（return）一個安全的空「籃子（[]）」。
        return []

# 我們用「def」來 定義（define）一個函式，名叫「write_projects_data」。
# 它的作用是將新的專案列表寫回文件。
def write_projects_data(data: List[Dict[str, Any]]):
    # TAG: DECOUPLE (解耦)
    # 這個函式同樣將「寫入」任務，完全委託給了 I/O 網關。
    try:
        # 我們用「def」來 定義（define）一個簡單的回調函式。
        # 它的作用就是用我們傳入的「新數據（data）」，去完全替換掉「舊數據（_）」。
        def overwrite_callback(_):
            return data
        
        # 我們調用網關，執行這個「覆蓋寫入」事務。
        safe_read_modify_write(PROJECTS_FILE, overwrite_callback, serializer='json')
    # 如果（if）網關報告了任何 I/O 錯誤...
    except IOError as e:
        # ...我們就用「raise」關鍵字，將這個錯誤包裝成一個新的「IOError」異常，再向上拋出。
        # 這樣，更高層的調用者（如 main_dispatcher）就能捕獲到這個失敗信號。
        raise IOError(f"寫入專案文件時失敗: {e}")


# 這是一個內部使用的輔助函式，用於從一個專案的數據中，提取出它所有目標文件的路徑。
def _get_targets_from_project(project_data):
    # (此函式邏輯簡單直觀，暫不添加註解，以保持極簡)
    targets = project_data.get('target_files')
    if isinstance(targets, list) and targets: return targets
    output = project_data.get('output_file')
    if isinstance(output, list) and output: return output
    if isinstance(output, str) and output.strip(): return [output]
    return []

# --- 統一更新入口 ---
# 這個函式負責執行一次完整的「單文件更新」流程。
def _run_single_update_workflow(project_path: str, target_doc: str) -> Tuple[int, str]:
    # (此函式在之前的重構中已添加過註解，且邏輯未變，此處保持簡潔，暫不重複註解)
    if not isinstance(project_path, str) or not os.path.isdir(project_path):
        return (2, f"【更新失敗】: 專案路徑不存在或無效 -> {project_path}")
    if not isinstance(target_doc, str) or not target_doc.strip():
        return (1, "【更新失敗】: 目標文件路徑參數不合法。")
    if not os.path.isabs(target_doc):
        return (1, f"【更新失敗】: 目標文件需為絕對路徑 -> {target_doc}")

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [Daemon] INFO: 收到更新請求。使用唯一的標準工人: worker.py", file=sys.stderr)

    try:
        with open(target_doc, 'r', encoding='utf-8') as f:
            old_content = f.read()
    except FileNotFoundError:
        old_content = ""
    except Exception as e:
        err = f"[DAEMON:READ] 讀取目標文件時發生意外錯誤: {e}"
        return (3, err)

    exit_code, result = execute_update_workflow(project_path, target_doc, old_content)

    timestamp_done = time.strftime('%Y-%m-%d %H:%M:%S')
    status = "成功" if exit_code == 0 else "失敗"
    print(f"[{timestamp_done}] [Daemon] INFO: 更新流程執行完畢。狀態: {status}", file=sys.stderr)
        
    return (exit_code, result)


# --- 命令處理函式 ---

# 處理「list_projects」命令。
def handle_list_projects():
    # 它只做一件事：調用我們自己的「read_projects_data」函式。
    return read_projects_data()

# 處理「add_project」命令。
def handle_add_project(args: List[str]):
    if len(args) != 3:
        raise ValueError("【新增失敗】：參數數量不正確，需要 3 個。")
    
    name, path, output_file = args
    clean_path = normalize_path(path)
    clean_output_file = normalize_path(output_file)

    if not os.path.isabs(clean_path) or not os.path.isabs(clean_output_file):
        raise ValueError("【新增失敗】：所有路徑都必須是絕對路徑。")
    
    parent_dir = os.path.dirname(clean_output_file)
    if parent_dir and not os.path.isdir(parent_dir):
        raise IOError(f"【新增失敗】：目標文件所在的資料夾不存在 -> {parent_dir}")

    if not validate_paths_exist([clean_path]):
        raise IOError(f"【新增失敗】：專案目錄路徑不存在 -> {clean_path}")
    
    # 我們用「def」來 定義（define）一個「新增」的回調函式。
    # 它的所有邏輯，都將在 I/O 網關的安全鎖內被執行。
    def add_callback(projects_data):
        # 在這裡，我們執行所有關於「新增」的業務邏輯檢查。
        if any(p.get('name') == name for p in projects_data):
            raise ValueError(f"專案別名 '{name}' 已被佔用。")
        if any(normalize_path(p.get('path', '')) == clean_path for p in projects_data):
            raise ValueError(f"專案路徑 '{clean_path}' 已被其他專案監控。")
        for p in projects_data:
            if any(normalize_path(target) == clean_output_file for target in _get_targets_from_project(p)):
                raise ValueError(f"目標文件 '{clean_output_file}' 已被專案 '{p.get('name')}' 使用。")
        
        # 我們創建一個新的專案「盒子（{}）」。
        new_project = {
            "uuid": str(uuid.uuid4()), "name": name, "path": clean_path,
            "output_file": [clean_output_file], "target_files": [clean_output_file],
        }
        # 我們把這個新盒子，追加（append）到專案列表這個大「籃子」裡。
        projects_data.append(new_project)
        # 最後，返回（return）這個被修改過的、包含了新專案的完整列表。
        return projects_data

    # 我們調用 I/O 網關，讓它去執行這個「新增」事務。
    safe_read_modify_write(PROJECTS_FILE, add_callback, serializer='json')

# 處理「edit_project」命令。
def handle_edit_project(args: List[str]):
    if len(args) != 3:
        raise ValueError("【編輯失敗】：參數數量不正確。")
    
    uuid_to_edit, field, new_value = args
    allowed_fields = ['name', 'path', 'output_file']
    if field not in allowed_fields:
        raise ValueError(f"無效的欄位名稱 '{field}'。")

    # 我們定義一個「編輯」的回調函式。
    def edit_callback(projects_data):
        # (這部分業務邏輯與 add_callback 類似，暫不重複註解以保持簡潔)
        project_to_edit = next((p for p in projects_data if p.get('uuid') == uuid_to_edit), None)
        if project_to_edit is None:
            raise ValueError(f"未找到具有該 UUID 的專案 '{uuid_to_edit}'。")
        
        other_projects = [p for p in projects_data if p.get('uuid') != uuid_to_edit]
        
        if field == 'name':
            if any(p.get('name') == new_value for p in other_projects):
                raise ValueError(f"新的專案別名 '{new_value}' 已被佔用。")
            project_to_edit['name'] = new_value
        elif field == 'path':
            clean_new_path = normalize_path(new_value)
            if not os.path.isabs(clean_new_path) or not validate_paths_exist([clean_new_path]):
                raise ValueError(f"新的路徑無效或不存在 -> {clean_new_path}")
            if any(normalize_path(p.get('path', '')) == clean_new_path for p in other_projects):
                raise ValueError(f"新的專案路徑 '{clean_new_path}' 已被其他專案監控。")
            project_to_edit['path'] = clean_new_path
        elif field == 'output_file':
            clean_new_output_file = normalize_path(new_value)
            if not os.path.isabs(clean_new_output_file):
                raise ValueError("新的目標文件路徑必須是絕對路徑。")
            for p in other_projects:
                if any(normalize_path(target) == clean_new_output_file for target in _get_targets_from_project(p)):
                    raise ValueError(f"目標文件 '{clean_new_output_file}' 已被專案 '{p.get('name')}' 使用。")
            project_to_edit['output_file'] = [clean_new_output_file]
            project_to_edit['target_files'] = [clean_new_output_file]
            
        return projects_data

    # 我們調用 I/O 網關，讓它去執行這個「編輯」事務。
    safe_read_modify_write(PROJECTS_FILE, edit_callback, serializer='json')

# 處理「delete_project」命令。
def handle_delete_project(args: List[str]):
    if len(args) != 1:
        raise ValueError("【刪除失敗】：需要 1 個參數 (uuid)。")
    uuid_to_delete = args[0]

    # 我們定義一個「刪除」的回調函式。
    def delete_callback(projects_data):
        initial_len = len(projects_data)
        # 我們用一個「列表推導式」，來創建一個不包含要刪除專案的新列表。
        new_projects = [p for p in projects_data if p.get('uuid') != uuid_to_delete]
        # 如果新舊列表的長度一樣，說明沒有找到要刪除的專案。
        if len(new_projects) == initial_len:
            raise ValueError(f"未找到具有該 UUID 的專案 '{uuid_to_delete}'。")
        return new_projects

    # 我們調用 I/O 網關，讓它去執行這個「刪除」事務。
    safe_read_modify_write(PROJECTS_FILE, delete_callback, serializer='json')

# 處理「manual_update」命令。
def handle_manual_update(args: List[str]):
    if len(args) != 1:
        raise ValueError("【手動更新失敗】：需要 1 個參數 (uuid)。")
    uuid_to_update = args[0]

    # TAG: HACK
    # 這裡我們先「讀取」一次，是為了獲取專案的路徑配置。
    # 這與後續的「寫入」是兩個獨立的事務，理論上存在競爭條件的風險，
    # 但在單用戶操作場景下，風險極低。這是為了簡化邏輯而做出的權衡。
    projects_data = read_projects_data()
    selected_project = next((p for p in projects_data if p.get('uuid') == uuid_to_update), None)
    
    if not selected_project:
        raise ValueError(f"未找到具有該 UUID 的專案 '{uuid_to_update}'。")

    project_path = selected_project.get('path')
    targets = _get_targets_from_project(selected_project)
    target_doc_path = targets[0] if targets else None

    if not project_path or not target_doc_path:
        raise ValueError(f"專案 '{selected_project.get('name')}' 缺少有效的路徑配置。")

    # 我們調用「_run_single_update_workflow」來獲取更新後的目錄樹內容。
    exit_code, formatted_tree_block = _run_single_update_workflow(project_path, target_doc_path)
    if exit_code != 0:
        raise RuntimeError(f"底層工人執行失敗:\n{formatted_tree_block}")

    # 我們定義一個「更新 MD 文件」的回調函式。
    def update_md_callback(full_old_content):
        # (這部分拼接邏輯與之前版本相同，暫不重複註解)
        start_marker = "<!-- AUTO_TREE_START -->"
        end_marker = "<!-- AUTO_TREE_END -->"
        if start_marker in full_old_content and end_marker in full_old_content:
            head = full_old_content.split(start_marker)[0]
            tail = full_old_content.split(end_marker, 1)[1]
            return f"{head}{start_marker}\n{formatted_tree_block.strip()}\n{end_marker}{tail}"
        else:
            return f"{full_old_content.rstrip()}\n\n{start_marker}\n{formatted_tree_block.strip()}\n{end_marker}".lstrip()

    # 我們調用 I/O 網關，讓它去執行這個「更新 MD 文件」的事務。
    # 注意，這裡的序列化器是「text」，因為我們處理的是純文本。
    safe_read_modify_write(target_doc_path, update_md_callback, serializer='text')

# 處理「manual_direct」命令。
def handle_manual_direct(args: List[str]):
    # (此函式邏輯與 handle_manual_update 高度相似，暫不重複註解以保持簡潔)
    if len(args) != 2:
        raise ValueError("【自由更新失敗】：需要 2 個參數 (project_path, target_doc_path)。")
    
    project_path, target_doc_path = map(normalize_path, args)
    
    if not os.path.isdir(project_path):
        raise IOError(f"專案目錄不存在或無效 -> {project_path}")

    exit_code, formatted_tree_block = _run_single_update_workflow(project_path, target_doc_path)
    if exit_code != 0:
        raise RuntimeError(f"底層工人執行失敗:\n{formatted_tree_block}")

    def update_md_callback(full_old_content):
        start_marker = "<!-- AUTO_TREE_START -->"
        end_marker = "<!-- AUTO_TREE_END -->"
        if start_marker in full_old_content and end_marker in full_old_content:
            head = full_old_content.split(start_marker)[0]
            tail = full_old_content.split(end_marker, 1)[1]
            return f"{head}{start_marker}\n{formatted_tree_block.strip()}\n{end_marker}{tail}"
        else:
            return f"{full_old_content.rstrip()}\n\n{start_marker}\n{formatted_tree_block.strip()}\n{end_marker}".lstrip()

    safe_read_modify_write(target_doc_path, update_md_callback, serializer='text')


# --- 總調度中心 ---
# 這個函式像一個電話總機，負責將來自命令行的指令，轉接到對應的處理函式。
def main_dispatcher(argv: List[str]):
    if not argv:
        print("錯誤：未提供任何命令。", file=sys.stderr)
        return 1

    command = argv[0]
    args = argv[1:]

    try:
        # 我們用「if...elif...」結構，來根據指令（command）進行分派。
        if command == 'ping':
            print("PONG")
        elif command == 'list_projects':
            projects = handle_list_projects()
            print(json.dumps(projects, indent=2, ensure_ascii=False))
        elif command == 'add_project':
            handle_add_project(args)
            print("OK")
        elif command == 'edit_project':
            handle_edit_project(args)
            print("OK")
        elif command == 'delete_project':
            handle_delete_project(args)
            print("OK")
        elif command == 'manual_update':
            handle_manual_update(args)
            print("OK")
        elif command == 'manual_direct':
            handle_manual_direct(args)
            print("OK")
        else:
            print(f"錯誤：未知命令 '{command}'。", file=sys.stderr)
            return 1
        
        # 如果所有操作都順利完成，就 返回（return）一個代表「成功」的退出碼 0。
        return 0

    # TAG: DEFENSE
    # 這裡是一個全局的「安全網」。它負責捕獲所有處理函式可能拋出的已知異常。
    except (ValueError, IOError, RuntimeError) as e:
        # 我們將捕獲到的異常信息，打印（print）到「標準錯誤流（stderr）」。
        print(str(e), file=sys.stderr)
        # 然後 返回（return）一個代表「業務邏輯錯誤」的退出碼 1。
        return 1
    # 這是最後一道防線，用於捕獲所有未知的、意外的錯誤。
    except Exception as e:
        print(f"【守護進程發生未知致命錯誤】：{e}", file=sys.stderr)
        # 返回一個特殊的退出碼 99，代表發生了嚴重的系統級錯誤。
        return 99

# --- 主執行入口 ---
# 這是一個 Python 的標準寫法。
# 它確保只有當這個文件被直接執行時，main() 函式才會被調用。
if __name__ == "__main__":
    # 我們調用「總調度中心」，並將命令行參數（除了腳本名本身）傳遞給它。
    exit_code = main_dispatcher(sys.argv[1:])
    # 我們用「sys.exit()」將「總調度中心」返回的退出碼，傳遞給操作系統。
    sys.exit(exit_code)
