# src/core/daemon.py

# 我們需要 導入（import）一系列 Python 內建的工具和我們自己的專家模塊。
import json
import uuid
import os
import sys
import time
import signal
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

# 我們定義 temp 目錄的默認路徑。
TEMP_DIR = os.path.join(project_root, 'temp')

def is_self_project_path(path: str) -> bool:
    """
    判斷給定路徑是否位於 laplace_sentry_control_v2 專案內部。
    用來避免「自我監控」。
    """
    abs_path = os.path.abspath(path)
    root = project_root

    # 統一補上結尾的分隔符，避免 /home/.../laplace_sentry_control_v2/tests
    # 與 /home/.../laplace_sentry_control_v2 混在一起判斷錯誤。
    if not root.endswith(os.sep):
        root = root + os.sep

    # 兩種情況都算「自己」：
    # 1. 目標路徑剛好就是專案根目錄
    # 2. 目標路徑位於專案根目錄之下（例如 .../laplace_sentry_control_v2/tests）
    return abs_path == project_root or abs_path.startswith(root)


# --- 【v5.0 哨兵管理】 ---
# 理由：創建一個全局的「戶口名簿」，用來跟蹤所有正在運行的哨兵進程。
# 它的鍵(key)是專案的 uuid，值(value)將是 subprocess.Popen 返回的進程對象。
running_sentries: Dict[str, Any] = {}

# --- 用下面的代碼，完整替換舊的 _get_projects_file_path ---
def get_projects_file_path(provided_path: Optional[str] = None) -> str:
    """
    【權威路徑來源】
    依賴注入的核心。優先使用外部提供的路徑。
    如果未提供，則根據環境變數決定是返回測試路徑還是生產路徑。
    """
    if provided_path:
        return provided_path
    
    if 'TEST_PROJECTS_FILE' in os.environ:
        return os.environ['TEST_PROJECTS_FILE']
    
    # 我們需要 project_root，確保它在函式內部可見
    project_root_for_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(project_root_for_path, 'data', 'projects.json')



# --- 數據庫輔助函式 (現在由 I/O 網關代理) ---

# 我們用「def」來 定義（define）一個函式，名叫「read_projects_data」。
# 它的作用是讀取專案列表。
def read_projects_data(file_path: str) -> List[Dict[str, Any]]:
    # TAG: DECOUPLE (解耦)
    # 這個函式現在的職責非常單純：它將「讀取」這個具體任務，完全委託給了 I/O 網關。
    try:
        # 我們用「def」來 定義（define）一個什麼都不做的「回調函式」。
        def read_only_callback(data):
            return data
        
        # 【v4.1 核心修改】我們現在調用 I/O 網關，並準備接收一個元組作為返回結果。
        # 這個元組包含兩個部分：(處理後的數據, 是否從備份中恢復的標誌)
        new_data, restored = safe_read_modify_write(file_path, read_only_callback, serializer='json')
        
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
def write_projects_data(data: List[Dict[str, Any]], file_path: str):
    # TAG: DECOUPLE (解耦)
    # 這個函式同樣將「寫入」任務，完全委託給了 I/O 網關。
    try:
        # 我們用「def」來 定義（define）一個簡單的「覆蓋寫入」回調函式。
        def overwrite_callback(_):
            return data
        
        # 【v4.1 核心修改】我們同樣準備接收 I/O 網關返回的元組。
        # 在這裡，我們其實不關心寫入後的數據是什麼，所以可以用「_」來忽略它。
        _, restored = safe_read_modify_write(file_path, overwrite_callback, serializer='json')
        
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

def handle_list_projects(projects_file_path: Optional[str] = None):

        # 【TECH-DEBT-STATELESS-SENTRY 核心改造】
    # 理由：在執行任何操作之前，先進行一次「全國人口普查」，清理掉所有名存實亡的「殭屍戶籍」。
    try:
        for filename in os.listdir(TEMP_DIR):
            if filename.endswith(".sentry"):
                pid_file_path = os.path.join(TEMP_DIR, filename)
                try:
                    pid = int(filename.split('.')[0])
                    # 檢查 PID 是否真實存在於操作系統中
                    # os.kill(pid, 0) 是一個絕妙的技巧：它不發送任何信號，但如果進程不存在，它會拋出 ProcessLookupError。
                    os.kill(pid, 0)
                    # 如果代碼能執行到這裡，說明 PID 是真實存活的。
                    # 現在，我們檢查內存中是否有它的記錄。
                    
                    # 我們需要讀取文件內容來獲取 UUID
                    with open(pid_file_path, 'r', encoding='utf-8') as f:
                        sentry_uuid = f.read().strip()

                    if sentry_uuid and sentry_uuid not in running_sentries:
                        # 這就是一個「合法但失憶」的哨兵！我們需要為它恢復記憶。
                        print(f"【狀態恢復】：發現運存活的哨兵 (PID: {pid}, UUID: {sentry_uuid})，但內存中無記錄。正在為其恢復狀態...", file=sys.stderr)
                        # 我們無法直接恢復出一個完美的 Popen 對象，因為我們沒有它的 stdin/stdout 等句柄。
                        # 但在當前的架構下，我們至少可以創建一個「代理」對象，它有 .pid 屬性，並且 .poll() 能正常工作。
                        # 一個更簡單、更健壯的做法是，只在 running_sentries 中存儲 PID。
                        # 但為了最小化改動，我們創建一個最簡單的、能通過測試的對象。
                        # HACK: 創建一個「代理」進程對象。這是一個簡化的表示，主要用於狀態檢查。
                        # 在 Python 的 `subprocess` 模塊中，沒有一個公開的、可以根據 PID 直接創建 Popen 對象的方法。
                        # 這是一個合理的簡化，因為我們後續的操作（如 stop）是基於 PID 的，而不是 Popen 對象本身。
                        class PidProxy:
                            def __init__(self, pid):
                                self.pid = pid
                            def poll(self):
                                try:
                                    # 再次使用 os.kill(pid, 0) 來檢查進程是否還活著
                                    os.kill(self.pid, 0)
                                    return None # 如果還活著，poll() 應該返回 None
                                except ProcessLookupError:
                                    return 1 # 如果已經死了，返回一個非零退出碼
                            def kill(self):
                                try:
                                    os.kill(self.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass # 如果已經死了，就什麼都不做

                        running_sentries[sentry_uuid] = PidProxy(pid)


                except (ValueError, ProcessLookupError):
                    # 如果 PID 無效，或進程已死亡，這就是一個「殭屍戶籍」。
                    print(f"【殭屍普查】：發現無效或已死亡的戶籍文件 {filename}，正在自動清理...", file=sys.stderr)
                    try:
                        os.remove(pid_file_path)
                    except OSError as e:
                        print(f"【殭屍普查警告】：清理殭屍戶籍 {filename} 時失敗: {e}", file=sys.stderr)
                except Exception:
                    # 忽略其他權限問題等，保持普查的健壯性。
                    continue
    except OSError as e:
        print(f"【殭屍普查警告】：掃描戶籍登記處 ({TEMP_DIR}) 時發生 I/O 錯誤: {e}", file=sys.stderr)

    PROJECTS_FILE = get_projects_file_path(projects_file_path)

    projects_data = read_projects_data(PROJECTS_FILE)
    project_map = {p['uuid']: p for p in projects_data}

    # 步驟 1: 先為所有專案設置一個默認的 'stopped' 狀態
    for project in project_map.values():
        project['status'] = 'stopped'

    # 步驟 2: 然後，再進行無差別的路徑有效性檢查，覆蓋掉那些路徑失效的專案狀態
    # --- 【ADHOC-002 巡邏升級】---
    for project in project_map.values():
        is_path_valid = os.path.isdir(project.get('path', ''))
        if not is_path_valid:
            project['status'] = 'invalid_path'
    # --- 巡邏升級結束 ---

    # 步驟 3: 最後，檢查正在運行的哨兵，將它們的狀態更新為 'running'
    sentry_uuids_to_check = list(running_sentries.keys())
    for uuid in sentry_uuids_to_check:
        process = running_sentries.get(uuid)
        if not process: continue

        project_config = project_map.get(uuid)
        
        is_alive = process.poll() is None
        # 【修正】這裡的 is_path_valid 檢查也需要更新，以反映最新的狀態
        is_path_valid_for_running = project_config and project_config.get('status') != 'invalid_path'

        if is_alive and is_path_valid_for_running:
            if uuid in project_map:
                project_map[uuid]['status'] = 'running'
        else:
            # ... 殭屍自愈邏輯保持不變 ...
            print(f"【殭屍自愈】: 偵測到失效哨兵 (UUID: {uuid}, PID: {process.pid})。原因: "
                f"進程存活={is_alive}, 路徑有效={is_path_valid_for_running}。正在清理...", file=sys.stderr)
            try:
                process.kill()
            except Exception:
                pass
            finally:
                if uuid in running_sentries:
                    del running_sentries[uuid]
                if uuid in project_map:
                    # 即使是殭屍，也要確保它最終顯示為 'invalid_path' 如果路徑真的失效了
                    if not (project_config and os.path.isdir(project_config.get('path', ''))):
                        project_map[uuid]['status'] = 'invalid_path'

    # 步驟 4: 【任務 2.3.3】檢查哨兵的「靜默信號」，將處於靜默狀態的專案標記為 'muting'
    for project in project_map.values():
        uuid = project.get('uuid')
        if not uuid:
            continue
        
        # 構造 .sentry_status 文件的路徑（哨兵工人寫入到 /tmp/ 目錄）
        status_file_path = f"/tmp/{uuid}.sentry_status"
        
        # 嘗試讀取文件
        try:
            if os.path.exists(status_file_path):
                with open(status_file_path, 'r', encoding='utf-8') as f:
                    muted_paths = json.load(f)
                
                # 只有當靜默列表非空，且專案狀態不是 'invalid_path' 時，才覆蓋為 'muting'
                if isinstance(muted_paths, list) and len(muted_paths) > 0:
                    if project.get('status') != 'invalid_path':
                        project['status'] = 'muting'
        except (json.JSONDecodeError, IOError) as e:
            # 如果文件損壞或讀取失敗，我們選擇「靜默地忽略」，不影響其他狀態判定
            print(f"【靜默狀態檢查警告】：讀取 {status_file_path} 時失敗: {e}", file=sys.stderr)
            continue


    return list(project_map.values())


def handle_add_project(args: List[str], projects_file_path: Optional[str] = None):
    PROJECTS_FILE = get_projects_file_path(projects_file_path)

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
                    
            abs_project_path = os.path.abspath(clean_path)
            abs_out = os.path.abspath(clean_output_file)

            abs_project_path = os.path.abspath(clean_path)
            abs_out = os.path.abspath(clean_output_file)

            # ✅ 只禁止寫進「哨兵自己專案」裡，不再禁止寫進被監控專案。
            if is_self_project_path(abs_out):
                raise ValueError(
                    f"【新增失敗】: output_file 指向哨兵自身專案路徑\n"
                    f"  ↳ 專案根目錄: {project_root}\n"
                    f"  ↳ 寫入路徑: {abs_out}\n"
                    f"為避免哨兵監控並改寫自身系統檔案，已拒絕加入專案。"
                )

        
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
def handle_edit_project(args: List[str], projects_file_path: Optional[str] = None):
    PROJECTS_FILE = get_projects_file_path(projects_file_path)
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
            
            abs_project_path = os.path.abspath(project_to_edit['path'])
            abs_new_out = os.path.abspath(clean_new_output_file)

            # ✅ 一樣只禁止寫進哨兵自身專案
            if is_self_project_path(abs_new_out):
                raise ValueError(
                    f"【編輯失敗】: output_file 指向哨兵自身專案路徑\n"
                    f"  ↳ 哨兵專案根目錄: {project_root}\n"
                    f"  ↳ 寫入路徑: {abs_new_out}\n"
                    f"為避免哨兵監控並改寫自身系統檔案，已拒絕修改。"
                )

            for p in other_projects:
                if any(normalize_path(target) == clean_new_output_file for target in _get_targets_from_project(p)):
                    raise ValueError(f"目標文件 '{clean_new_output_file}' 已被專案 '{p.get('name')}' 使用。")
            project_to_edit['output_file'] = [clean_new_output_file]
            project_to_edit['target_files'] = [clean_new_output_file]
            
        return projects_data

    # 我們調用 I/O 網關，讓它去執行這個「編輯」事務。
    safe_read_modify_write(PROJECTS_FILE, edit_callback, serializer='json')

def handle_delete_project(args: List[str], projects_file_path: Optional[str] = None):
    PROJECTS_FILE = get_projects_file_path(projects_file_path)

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



def handle_manual_update(args: List[str], projects_file_path: Optional[str] = None):
    PROJECTS_FILE = get_projects_file_path(projects_file_path)

    if len(args) != 1:
        raise ValueError("【手動更新失敗】：需要 1 個參數 (uuid)。")
    uuid_to_update = args[0]

    projects_data = read_projects_data(PROJECTS_FILE)

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
def handle_manual_direct(args: List[str], ignore_patterns: Optional[set] = None, projects_file_path: Optional[str] = None):
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

def handle_start_sentry(args: List[str], projects_file_path: Optional[str] = None):
    PROJECTS_FILE = get_projects_file_path(projects_file_path)

    if len(args) != 1:
        raise ValueError("【啟動失敗】：需要 1 個參數 (uuid)。")
    uuid_to_start = args[0]

    # 我們檢查一下這個哨兵是不是已經在執勤了。
    if uuid_to_start in running_sentries:
        raise ValueError(f"專案的哨兵已經在運行中。")

    projects_data = read_projects_data(PROJECTS_FILE)

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

    # --- 【ADHOC-002 啟動加固】在啟動前增加防爆牆 ---
    if not project_path or not os.path.isdir(project_path):
        raise IOError(f"【啟動失敗】: 專案 '{project_name}' 的監控路徑無效或不存在 -> {project_path}")
# --- 防爆牆結束 ---

    # 【v8.1.1 健壯性加固】
    # 理由：在啟動子進程前，必須確保所有關鍵參數都有效。
    if not project_path or not os.path.isdir(project_path):
        raise ValueError(f"專案 '{project_config.get('name')}' 的路徑無效或不存在: '{project_path}'")

    command = [python_executable, sentry_script_path, uuid_to_start, project_path]

    # 【OUTPUT-FILE-BLACKLIST 機制】
    # 理由:防止哨兵捕獲系統自身寫入 output_file 時產生的事件,避免監控迴圈。
    # 我們從專案配置中讀取 output_file 列表,並將其作為參數傳遞給哨兵。
    output_files = project_config.get('output_file', [])
    # 我們將列表轉為逗號分隔的字符串,方便命令行傳遞。
    output_files_str = ','.join(output_files) if output_files else ''
    # 我們將這個字符串作為第三個參數添加到命令中。
    command.append(output_files_str)

    try:
        # 我們以「追加模式(a)」打開日誌文件。
        log_file = open(log_file_path, 'a', encoding='utf-8')

        print(f"【守護進程】: 正在為專案 '{project_name}' 啟動哨兵...")
        print(f"【守護進程】: 命令: {' '.join(command)}")
        print(f"【守護進程】: 日誌將被寫入: {log_file_path}")

        # 【核心動作】我們使用 Popen 在背景啟動子進程。
        # 我們將它的 stdout 和 stderr 都重定向到我們打開的日誌文件中。
        process = subprocess.Popen(command, stdout=log_file, stderr=log_file, text=True)

                # 【TECH-DEBT-STATELESS-SENTRY 核心改造】
        # 理由：實現持久化的「出生登記」。
        # 我們在 Popen 成功後，立刻獲取新進程的 PID。
        pid = process.pid
        # 我們構造出這個哨兵的「戶籍文件」路徑。
        # 注意：我們需要一個統一的地方來管理 temp 目錄的路徑。
        # 我們先在文件頂部定義一個全局的 TEMP_DIR。
        pid_file_path = os.path.join(TEMP_DIR, f"{pid}.sentry")
        
        # 我們將專案的 UUID，寫入這個戶籍文件中。
        try:
            with open(pid_file_path, 'w', encoding='utf-8') as f:
                f.write(uuid_to_start)
        except IOError as e:
            # 如果戶籍登記失敗，這是一個致命錯誤。我們必須立刻終止剛剛啟動的進程，防止產生沒有戶口的「黑戶」。
            print(f"【守護進程致命錯誤】：為 PID {pid} 創建戶籍文件失敗: {e}", file=sys.stderr)
            process.kill() # 立即終止
            # 向上拋出一個更嚴重的異常，讓調用者知道啟動失敗了。
            raise RuntimeError(f"創建哨兵戶籍文件 {pid_file_path} 失敗。")


        # 【登記戶口】我們將這個新的進程對象，記錄到我們的「戶口名簿」中。
        running_sentries[uuid_to_start] = process

        print(f"【守護進程】: 哨兵已成功啟動。進程 PID: {process.pid}")

    except Exception as e:
        # 任何在啟動過程中發生的錯誤，都會被這個安全網捕獲。
        raise RuntimeError(f"啟動哨兵子進程時發生致命錯誤: {e}")

# 理由：為「停止哨兵」函式填充真實的、帶有日誌和錯誤處理的 terminate 邏輯。
def handle_stop_sentry(args: List[str], projects_file_path: Optional[str] = None):
    # 【TECH-DEBT-STATELESS-SENTRY 核心改造】
    # 理由：徹底重寫，使其從「基於內存」變為「基於文件系統」。
    if len(args) != 1:
        raise ValueError("【停止失敗】：需要 1 個參數 (uuid)。")
    uuid_to_stop = args[0]

    pid_to_kill = None
    pid_file_to_remove = None

    # 步驟 1: 掃描戶籍登記處 (temp 目錄)，查找目標的戶籍文件。
    try:
        for filename in os.listdir(TEMP_DIR):
            if filename.endswith(".sentry"):
                pid_file_path = os.path.join(TEMP_DIR, filename)
                try:
                    with open(pid_file_path, 'r', encoding='utf-8') as f:
                        file_content_uuid = f.read().strip()
                    
                    if file_content_uuid == uuid_to_stop:
                        # 找到了！我們從文件名中解析出 PID。
                        pid_to_kill = int(filename.split('.')[0])
                        pid_file_to_remove = pid_file_path
                        break # 找到就不需要再繼續掃描了
                except (IOError, ValueError):
                    # 如果文件讀取或解析失敗，就跳過這個損壞的戶籍文件。
                    print(f"【守護進程警告】：掃描戶籍文件 {pid_file_path} 時出錯，已跳過。", file=sys.stderr)
                    continue
    except OSError as e:
        raise IOError(f"【停止失敗】：掃描戶籍登記處 ({TEMP_DIR}) 時發生 I/O 錯誤: {e}")

    # 步驟 2: 如果沒有找到戶籍文件，說明該哨兵可能從未啟動或已被停止。
    if pid_to_kill is None:
        # 為了兼容舊的內存模式，我們也檢查一下內存。
        if uuid_to_stop in running_sentries:
            # 這是一種邊界情況：有內存記錄，但沒有戶籍文件。
            # 我們嘗試按舊方式清理，並給出警告。
            print(f"【守護進程警告】：在內存中找到哨兵 {uuid_to_stop}，但未找到其戶籍文件。將嘗試按舊方式停止。", file=sys.stderr)
            process_to_stop = running_sentries.pop(uuid_to_stop)
            try:
                process_to_stop.kill()
            except Exception:
                pass
            raise ValueError(f"專案的哨兵可能處於異常狀態，已嘗試強制清理。")
        else:
            raise ValueError(f"未找到正在運行的、屬於專案 {uuid_to_stop} 的哨兵。")

    # 步驟 3: 執行「死亡註銷」流程。
    print(f"【守護進程】: 正在嘗試停止哨兵 (PID: {pid_to_kill})...")
    try:
        # 我們使用 os.kill 來發送終止信號。這比 Popen 對象更通用。
        # 我們需要檢查進程是否存在，以避免對一個已死亡的 PID 操作而引發異常。
        import signal
        os.kill(pid_to_kill, signal.SIGTERM) # 發送一個優雅的終止信號
        print(f"【守護進程】: 哨兵 (PID: {pid_to_kill}) 已成功發送終止信號。")
    except ProcessLookupError:
        # 如果進程已經不存在了（可能已經自己崩潰了），這不是一個錯誤。
        print(f"【守護進程】: 哨兵 (PID: {pid_to_kill}) 在嘗試停止前就已不存在。")
    except Exception as e:
        # 捕獲所有其他在終止過程中可能發生的意外。
        raise RuntimeError(f"停止哨兵 (PID: {pid_to_kill}) 時發生致命錯誤: {e}")
    finally:
        # 步驟 4: 無論終止是否成功，都必須清理現場。
        # 刪除戶籍文件
        if pid_file_to_remove and os.path.exists(pid_file_to_remove):
            try:
                os.remove(pid_file_to_remove)
                print(f"【守護進程】: 已成功註銷戶籍文件 {os.path.basename(pid_file_to_remove)}。")
            except OSError as e:
                print(f"【守護進程警告】：刪除戶籍文件 {pid_file_to_remove} 時失敗: {e}", file=sys.stderr)
        
        # 從內存中也移除（如果存在的話）
        if uuid_to_stop in running_sentries:
            del running_sentries[uuid_to_stop]


# --- 總調度中心 ---
# 這個函式像一個電話總機，負責將來自命令行的指令，轉接到對應的處理函式。
def main_dispatcher(argv: List[str], **kwargs):
    if not argv:
        print("錯誤：未提供任何命令。", file=sys.stderr)
        return 1

    command = argv[0]
    args = argv[1:]

    # --- 【v9.1 依賴注入核心改造】 ---
    # 我們用 .get() 方法，從 kwargs 字典中，安全地獲取 projects_file_path。
    # 如果找不到，它會默認返回 None，這與我們之前的行為完全一致。
    projects_file_path = kwargs.get('projects_file_path')

    try:
        # 我們用「if...elif...」結構，來根據指令（command）進行分派。
        if command == 'ping':
            print("PONG")
        elif command == 'list_projects':
            projects = handle_list_projects(projects_file_path=projects_file_path)
            print(json.dumps(projects, indent=2, ensure_ascii=False))
        elif command == 'add_project':
            handle_add_project(args, projects_file_path=projects_file_path)
            print("OK")
        elif command == 'edit_project':
            handle_edit_project(args, projects_file_path=projects_file_path)
            print("OK")
        elif command == 'delete_project':
            handle_delete_project(args, projects_file_path=projects_file_path)
            print("OK")
        elif command == 'manual_update':
            handle_manual_update(args, projects_file_path=projects_file_path)
            print("OK")
        elif command == 'manual_direct':
            handle_manual_direct(args, projects_file_path=projects_file_path)
            print("OK")
        elif command == 'start_sentry':
            handle_start_sentry(args, projects_file_path=projects_file_path)
            print("OK")
        elif command == 'stop_sentry':
            handle_stop_sentry(args, projects_file_path=projects_file_path)
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
                # 【核心改造】我們檢查一個特殊的環境變數，來判斷當前是否處於測試模式。
        if 'LAPLACE_TEST_MODE' in os.environ:
            # 如果是，我們就將捕獲到的異常，原封不動地向上拋出，讓 unittest 框架能接到。
            raise e
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
