# src/core/daemon.py

# 我們需要 導入（import）一系列 Python 內建的工具和我們自己的專家模塊。
import json
import uuid
import os
import sys
import time
from typing import Optional, Tuple, List, Dict, Any
import subprocess

# --- 【v4.0 依賴注入】 ---
# 我們現在只導入我們需要的、真正屬於「專家」的工具。
# 從我們自己的「路徑專家（path）」模塊中，導入（import）「正規化路徑」和「驗證路徑存在」這兩個函式。
from .path import normalize_path, validate_paths_exist
# 從我們自己的「工人專家（worker）」模塊中，導入（import）「執行更新工作流」這個函式。
from .worker import execute_update_workflow
# 【核心重構】我們導入全新的「I/O 網關」，它是我們所有文件操作的唯一安全出口。
from .io_gateway import safe_read_modify_write
# 【核心重構】我們導入全新的「I/O 網關」，以及它可能會發射的「警告信號彈」。
from .io_gateway import safe_read_modify_write, DataRestoredFromBackupWarning


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

# --- 【v5.0 哨兵管理】 ---
# 理由：創建一個全局的「戶口名簿」，用來跟蹤所有正在運行的哨兵進程。
# 它的鍵(key)是專案的 uuid，值(value)將是 subprocess.Popen 返回的進程對象。
running_sentries: Dict[str, Any] = {}

# --- 數據庫輔助函式 (現在由 I/O 網關代理) ---

# 我們用「def」來 定義（define）一個函式，名叫「read_projects_data」。
# 它的作用是讀取專案列表。
def read_projects_data() -> List[Dict[str, Any]]:
    # TAG: DECOUPLE (解耦)
    # 這個函式現在的職責非常單純：它將「讀取」這個具體任務，完全委託給了 I/O 網關。
    try:
        # 我們用「def」來 定義（define）一個什麼都不做的「回調函式」。
        def read_only_callback(data):
            return data
        
        # 【v4.1 核心修改】我們現在調用 I/O 網關，並準備接收一個元組作為返回結果。
        # 這個元組包含兩個部分：(處理後的數據, 是否從備份中恢復的標誌)
        new_data, restored = safe_read_modify_write(PROJECTS_FILE, read_only_callback, serializer='json')
        
        # 我們用「if」來判斷，如果（if）「已恢復」的標誌（restored）為 True...
        if restored:
            # ...我們就用「raise」關鍵字，拋出我們自訂的「警告信號彈」。
            # 這個信號彈會被更高層的 main.py 捕獲，並向您顯示友好的提示。
            raise DataRestoredFromBackupWarning("專案列表已從備份恢復，請檢查。")
            
        # 如果沒有從備份恢復，我們就正常地 返回（return）讀取到的數據。
        return new_data

    # 我們用「except DataRestoredFromBackupWarning」來精準捕獲我們自己的「警告信號彈」。
    except DataRestoredFromBackupWarning:
        # 當捕獲到它時，我們必須再次用「raise」將它向上拋出，確保 main.py 能收到。
        raise
    # 我們用「except IOError」來捕獲網關可能報告的其他所有真正的 I/O 錯誤。
    except IOError as e:
        print(f"【守護進程警告】：讀取專案文件時出錯: {e}", file=sys.stderr)
        return []

# 我們用「def」來 定義（define）一個函式，名叫「write_projects_data」。
# 它的作用是將新的專案列表寫回文件。
def write_projects_data(data: List[Dict[str, Any]]):
    # TAG: DECOUPLE (解耦)
    # 這個函式同樣將「寫入」任務，完全委託給了 I/O 網關。
    try:
        # 我們用「def」來 定義（define）一個簡單的「覆蓋寫入」回調函式。
        def overwrite_callback(_):
            return data
        
        # 【v4.1 核心修改】我們同樣準備接收 I/O 網關返回的元組。
        # 在這裡，我們其實不關心寫入後的數據是什麼，所以可以用「_」來忽略它。
        _, restored = safe_read_modify_write(PROJECTS_FILE, overwrite_callback, serializer='json')
        
        # 我們同樣檢查「已恢復」的標誌。
        if restored:
            # 如果在寫入之前，I/O 網關發現文件是壞的並進行了恢復，我們同樣需要向上報告。
            raise DataRestoredFromBackupWarning("專案列表在寫入前檢測到損壞並已從備份恢復，請檢查。")

    # 我們同樣需要捕獲並再次拋出我們自己的「警告信號彈」。
    except DataRestoredFromBackupWarning:
        raise
    # 如果（if）網關報告了任何其他真正的 I/O 錯誤...
    except IOError as e:
        # ...我們就將其包裝成一個新的「IOError」異常，再向上拋出。
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
def _run_single_update_workflow(project_path: str, target_doc: str, ignore_patterns: Optional[set] = None) -> Tuple[int, str]:
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

    # 在 _run_single_update_workflow 函式內部
    exit_code, result = execute_update_workflow(project_path, target_doc, old_content, ignore_patterns=ignore_patterns)

    timestamp_done = time.strftime('%Y-%m-%d %H:%M:%S')
    status = "成功" if exit_code == 0 else "失敗"
    print(f"[{timestamp_done}] [Daemon] INFO: 更新流程執行完畢。狀態: {status}", file=sys.stderr)
        
    return (exit_code, result)


# --- 命令處理函式 ---

# 理由：為「列出專案」函式植入「PID存活性」+「路徑有效性」的雙重健康檢查。
def handle_list_projects():
    projects_data = read_projects_data()
    projects_with_status = []
    
    # 我們創建一個當前執勤哨兵的副本，以便在循環中安全地刪除元素。
    sentry_uuids_to_check = list(running_sentries.keys())

    # 我們先處理所有已註冊的專案，並為它們賦予初始狀態。
    project_map = {p['uuid']: p for p in projects_data}
    for uuid, project in project_map.items():
        project['status'] = 'stopped' # 默認都是停止狀態

    # 現在，我們開始遍歷所有正在執勤的哨兵，對他們進行體檢。
    for uuid in sentry_uuids_to_check:
        process = running_sentries.get(uuid)
        if not process: continue # 如果在檢查過程中已被移除，就跳過。

        # 我們從專案地圖中，獲取該哨兵對應的專案配置。
        project_config = project_map.get(uuid)
        
        # 【健康檢查 1: PID 存活性】
        is_alive = process.poll() is None
        # 【健康檢查 2: 路徑有效性】
        # 我們檢查專案配置是否存在，並且其 'path' 鍵對應的路徑是否是一個真實存在的目錄。
        is_path_valid = project_config and os.path.isdir(project_config.get('path', ''))

        # 如果哨兵活著，並且它監控的路徑也有效...
        if is_alive and is_path_valid:
            # ...我們才認為它是健康的「運行中」狀態。
            if uuid in project_map:
                project_map[uuid]['status'] = 'running'
        else:
            # 【殭屍自愈】只要上述兩個條件有任何一個不滿足，就視為「殭屍」！
            print(f"【殭屍自愈】: 偵測到失效哨兵 (UUID: {uuid}, PID: {process.pid})。原因: "
                f"進程存活={is_alive}, 路徑有效={is_path_valid}。正在清理...", file=sys.stderr)

            try:
                process.kill() # 強制終結殭屍進程
            except Exception:
                pass # 忽略終結過程中可能發生的錯誤（例如進程已經自己死了）
            finally:
                del running_sentries[uuid] # 將其從執勤名單中移除
                
                # 如果這個殭屍對應的專案還在我們的列表裡...
                if uuid in project_map:
                    # ...我們就將其狀態標記為「路徑失效」，以便前端顯示。
                    project_map[uuid]['status'] = 'invalid_path'

    # 最後，我們返回處理過的、帶有最新狀態的專案列表。
    return list(project_map.values())


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

    # 我們從專案的數據中，獲取 ignore_patterns。
    ignore_list = selected_project.get("ignore_patterns")
    # 我們檢查它是否是一個列表，如果是，就用 set() 將它轉換為一個集合。
    ignore_patterns = set(ignore_list) if isinstance(ignore_list, list) else None

    if not project_path or not target_doc_path:
        raise ValueError(f"專案 '{selected_project.get('name')}' 缺少有效的路徑配置。")

    # 我們調用「_run_single_update_workflow」來獲取更新後的目錄樹內容。
    exit_code, formatted_tree_block = _run_single_update_workflow(project_path, target_doc_path, ignore_patterns=ignore_patterns)
    
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
def handle_manual_direct(args: List[str], ignore_patterns: Optional[set] = None):    
    # (此函式邏輯與 handle_manual_update 高度相似，暫不重複註解以保持簡潔)
    if len(args) != 2:
        raise ValueError("【自由更新失敗】：需要 2 個參數 (project_path, target_doc_path)。")
    
    project_path, target_doc_path = map(normalize_path, args)

    if not os.path.isdir(project_path):
        raise IOError(f"專案目錄不存在或無效 -> {project_path}")

    exit_code, formatted_tree_block = _run_single_update_workflow(project_path, target_doc_path, ignore_patterns=ignore_patterns)
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

# 理由：為「啟動哨兵」函式填充真實的、帶有日誌管道和風險控制的 Popen 邏輯。
def handle_start_sentry(args: List[str]):
    if len(args) != 1:
        raise ValueError("【啟動失敗】：需要 1 個參數 (uuid)。")
    uuid_to_start = args[0]

    # 我們檢查一下這個哨兵是不是已經在執勤了。
    if uuid_to_start in running_sentries:
        raise ValueError(f"專案的哨兵已經在運行中。")

    # 我們讀取專案數據，找到對應的專案配置。
    projects_data = read_projects_data()
    project_config = next((p for p in projects_data if p.get('uuid') == uuid_to_start), None)

    if not project_config:
        raise ValueError(f"未找到具有該 UUID 的專案 '{uuid_to_start}'。")

    project_name = project_config.get("name", "Unnamed_Project")
    # 我們將專案名中的空格和特殊字符替換掉，以創建一個安全的文件名。
    log_filename = "".join(c if c.isalnum() else "_" for c in project_name) + ".log"
    log_dir = os.path.join(project_root, 'logs')
    log_file_path = os.path.join(log_dir, log_filename)

    # 我們確保 logs 目錄存在。
    os.makedirs(log_dir, exist_ok=True)

    # 我們定義要執行的命令。
    sentry_script_path = os.path.join(project_root, 'src', 'core', 'sentry_worker.py')
    # 【核心安全措施】我們不再依賴系統環境，而是明確指定使用當前運行的這個 Python 解釋器。
    python_executable = sys.executable
    project_path = project_config.get('path', '') # 獲取專案路徑

    command = [python_executable, sentry_script_path, uuid_to_start, project_path]

    try:
        # 我們以「追加模式(a)」打開日誌文件。
        log_file = open(log_file_path, 'a', encoding='utf-8')

        print(f"【守護進程】: 正在為專案 '{project_name}' 啟動哨兵...")
        print(f"【守護進程】: 命令: {' '.join(command)}")
        print(f"【守護進程】: 日誌將被寫入: {log_file_path}")

        # 【核心動作】我們使用 Popen 在背景啟動子進程。
        # 我們將它的 stdout 和 stderr 都重定向到我們打開的日誌文件中。
        process = subprocess.Popen(command, stdout=log_file, stderr=log_file, text=True)

        # 【登記戶口】我們將這個新的進程對象，記錄到我們的「戶口名簿」中。
        running_sentries[uuid_to_start] = process

        print(f"【守護進程】: 哨兵已成功啟動。進程 PID: {process.pid}")

    except Exception as e:
        # 任何在啟動過程中發生的錯誤，都會被這個安全網捕獲。
        raise RuntimeError(f"啟動哨兵子進程時發生致命錯誤: {e}")

# 理由：為「停止哨兵」函式填充真實的、帶有日誌和錯誤處理的 terminate 邏輯。
def handle_stop_sentry(args: List[str]):
    if len(args) != 1:
        raise ValueError("【停止失敗】：需要 1 個參數 (uuid)。")
    uuid_to_stop = args[0]

    # 我們先檢查一下這個哨兵是否在我們的「執勤名單」上。
    if uuid_to_stop not in running_sentries:
        raise ValueError(f"專案的哨兵並未在運行中，或從未被本程序啟動。")

    # 從「戶口名簿」中，獲取該哨兵的「進程對象」。
    process_to_stop = running_sentries[uuid_to_stop]
    pid = process_to_stop.pid

    print(f"【守護進程】: 正在嘗試停止哨兵 (PID: {pid})...")

    try:
        # 【核心動作】我們調用進程對象的 .terminate() 方法，向其發送終止信號。
        process_to_stop.terminate()
        # 我們等待一小段時間，給子進程一點反應時間來處理終止信號。
        process_to_stop.wait(timeout=5)
        print(f"【守護進程】: 哨兵 (PID: {pid}) 已成功發送終止信號。")

    except subprocess.TimeoutExpired:
        # 如果在 5 秒內，子進程還沒有終止，我們就採取更強硬的手段。
        print(f"【守護進程警告】: 哨兵 (PID: {pid}) 未能在 5 秒內響應，將強制終止。")
        process_to_stop.kill()
        print(f"【守護進程】: 哨兵 (PID: {pid}) 已被強制終止。")

    except Exception as e:
        # 捕獲所有其他在終止過程中可能發生的意外。
        raise RuntimeError(f"停止哨兵 (PID: {pid}) 時發生致命錯誤: {e}")

    finally:
        # 【註銷戶口】無論終止過程是否順利，我們都必須將它從「執勤名單」中移除。
        # 這是為了防止產生「殭屍記錄」。
        del running_sentries[uuid_to_stop]


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
        elif command == 'start_sentry':
            handle_start_sentry(args)
            print("OK")
        elif command == 'stop_sentry':
            handle_stop_sentry(args)
            print("OK")
        else:
            print(f"錯誤：未知命令 '{command}'。", file=sys.stderr)
            return 1
        
        # 如果所有操作都順利完成，就 返回（return）一個代表「成功」的退出碼 0。
        return 0

    # TAG: DEFENSE
    # 這裡是一個全局的「安全網」。它負責捕獲所有處理函式可能拋出的已知異常。

    # 我們首先專門捕獲那個「數據恢復」的警告。
    except DataRestoredFromBackupWarning as e:
        # 【v9.0 核心修改】我們不再將其當作錯誤，而是打印一條清晰的、引導性的提示訊息。
        print(f"【系統通知】偵測到設定檔損壞，並已從備份自動恢復。請從主菜單重新操作一次。", file=sys.stderr)
        # 我們返回一個特殊的退出碼 10，代表這是一個「需要用戶重試」的成功操作。
        return 10

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
