# main.py - 【v5.2 UX 終極優化版】

import sys
import os
import json
# 【承諾 1: 完整導入】一次性導入所有需要的類型，杜絕 "未定義" 錯誤。
from typing import Optional, Tuple, List, Dict, Any

# HACK: 解決模組導入問題的經典技巧
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 從後端導入我們唯一的依賴：daemon
from src.core import daemon

# --- 前端專用輔助函式 ---

def _call_daemon_and_get_output(command_and_args: List[str]) -> Tuple[int, str]:
    """
    【v-ADHOC-005 智能重試版】
    一個特殊的、只用於獲取後端輸出的內部函式。
    """
    from io import StringIO
    import contextlib

    temp_stdout = StringIO()
    temp_stderr = StringIO() # 我們也捕獲 stderr，以便在重試時保持安靜
    exit_code = -1

    # 我們將 daemon 的調用包裹在 try...except 中，以捕獲所有可能的異常
    try:
        with contextlib.redirect_stdout(temp_stdout), contextlib.redirect_stderr(temp_stderr):
            exit_code = daemon.main_dispatcher(command_and_args)
    except Exception as e:
        # 如果在調用過程中發生任何未知崩潰，我們打印錯誤並返回一個失敗碼。
        print(f"\n[前端致命錯誤]：在獲取輸出時，後端發生意外崩潰！\n  -> 原因: {e}", file=sys.stderr)
        return (99, "")

    # --- 【v-ADHOC-005 核心改造】 ---
    # 我們在這裡也加入對退出碼 10 的判斷
    if exit_code == 10:
        # 如果收到重試信號，我們就再次調用自己，獲取恢復後的、健康的數據。
        print("[前端日誌]：在獲取輸出時收到恢復信號(10)，正在自動重試...", file=sys.stderr)
        return _call_daemon_and_get_output(command_and_args)

    # 對於所有其他情況（包括成功 0 和其他失敗碼），我們都直接返回結果。
    output = temp_stdout.getvalue()
    return (exit_code, output)



def _call_daemon_and_show_feedback(command_and_args: List[str]) -> bool:
    """一個通用的、負責與後端交互並向用戶顯示回饋的函式。"""
    print("\n[前端]：正在向後端發送指令...")
    
    # TAG: ADHOC-001 - 優雅失敗
    # 我們將 daemon 的調用也包裹在 try...except 中，以捕獲它可能拋出的異常
    try:
        from io import StringIO
        import contextlib

        temp_stdout = StringIO()
        temp_stderr = StringIO() # 我們也捕獲 stderr
        exit_code = -1

        # 使用 contextlib.redirect_stdout/stderr 來捕獲所有輸出
        with contextlib.redirect_stdout(temp_stdout), contextlib.redirect_stderr(temp_stderr):
            exit_code = daemon.main_dispatcher(command_and_args)
        
        output = temp_stdout.getvalue()
        error_output = temp_stderr.getvalue()

        # --- 【v-ADHOC-005 核心改造】 ---
        # 我們現在要區分不同的退出碼
        if exit_code == 0:
            print("\033[92m[✓] 操作成功\033[0m") 
            if output.strip() and output.strip() != "OK":
                if command_and_args[0] != 'list_projects':
                    print("--- 後端返回信息 ---\n" + output)
            return True
        # 我們專門為退出碼 10 開闢一條新的處理路徑
        elif exit_code == 10:
            # 當收到這個信號時，我們知道後端已經完成了恢復，但需要前端重試。
            print("[前端日誌]：收到後端數據恢復信號(10)，正在自動重試...")
            # 我們在這裡，直接、無縫地再次調用自己，把同樣的指令再發送一次。
            # 這就是「原地重試」的核心。
            return _call_daemon_and_show_feedback(command_and_args)
        else:
            # 對於所有其他的非零退出碼，我們才認為是真正的失敗。
            print(f"\033[91m[✗] 操作失敗 (退出碼: {exit_code})\033[0m")
            if error_output.strip():
                print("--- 後端錯誤報告 ---\n" + error_output.strip())
            else:
                print("--- 後端未提供額外錯誤信息 ---")
            return False


    except daemon.DataRestoredFromBackupWarning as e:
        # 當捕獲到這個特殊的、非致命的警告時...
        print("\n" + "="*50)
        print("\033[93m[提示] 系統偵測到您的專案設定檔曾發生輕微損壞，並已自動從最近的備份中成功恢復。\033[0m")
        print("請您檢查一下當前的專案列表，確認最近的操作是否都已正確保存。")
        print(f"  (恢復自: {e})")
        print("="*50)
        # 我們返回 True，因為從用戶的角度看，操作最終是「成功」的，系統恢復了正常。
        return True

    except (json.JSONDecodeError, IOError) as e:
        # 針對 I/O 和 JSON 損壞的特定錯誤，給出更清晰的引導
        print(f"\033[91m[✗] 操作失敗：發生嚴重的 I/O 或數據文件錯誤。\033[0m")
        print("--- 錯誤詳情 ---")
        print(str(e))
        print("\n建議：請檢查 'data/projects.json' 文件是否存在或內容是否損壞。")
        return False
    except Exception as e:
        # 通用安全氣囊保持不變
        print(f"\n[前端致命錯誤]：調用後端時發生意外崩潰！\n  -> 原因: {e}", file=sys.stderr)
        return False


def _select_project(operation_name: str) -> Optional[Dict[str, Any]]:
    """【UX 核心】列出表格化的專案，讓用戶通過數字選擇。"""
    print(f"\n--- {operation_name} ---")
    exit_code, projects_json_str = _call_daemon_and_get_output(['list_projects'])
    

    if exit_code != 0:
        print("[前端]：獲取專案列表失敗！")
        return None

    try:
        projects = json.loads(projects_json_str)
        if not projects:
            print("目前沒有任何已註冊的專案。")
            return None
    except json.JSONDecodeError:
        print("[前端]：解析後端返回的專案列表時出錯！")
        return None

    # --- 【v5.5 狀態可視化】表格化顯示邏輯 ---
    # 我們在表頭中，新增一個「狀態」欄位。
    headers = {"status": "狀態", "no": "編號", "name": "專案別名"}

    # 我們為不同的狀態，定義好對應的圖標。
    status_icons = {
        "running": "[✅ 運行中]",
        "stopped": "[⛔️ 已停止]",
        "invalid_path": "[❌ 路徑失效]",
    }

    # 【手術 1 核心】我們在計算寬度時，也要考慮狀態圖標的寬度。
    widths = {key: len(title) for key, title in headers.items()}
    for i, p in enumerate(projects):
        status_text = status_icons.get(p.get('status'), "[❔ 未知]")
        widths['status'] = max(widths['status'], len(status_text))
        widths['no'] = max(widths['no'], len(str(i + 1)))
        widths['name'] = max(widths['name'], len(p.get('name', '')))

    # 【手術 1 核心】我們在打印表頭時，也加入「狀態」這一列。
    header_line = (f"  {headers['status']:<{widths['status']}}  "
                f"| {headers['no']:<{widths['no']}}  "
                f"| {headers['name']:<{widths['name']}}")
    print(header_line)
    print("-" * len(header_line))

    # 【注意】這裡我們暫時還打印舊的、沒有狀態的行，這是正常的。
    for i, p in enumerate(projects):
        # 我們根據專案的 status，從圖標字典中獲取對應的圖標。
        status_text = status_icons.get(p.get('status'), "[❔ 未知]")
        # 【手術 2 核心】我們在打印每一行時，將狀態圖標放在最前面。
        row_line = (f"  {status_text:<{widths['status']}}  "
                    f"| {str(i + 1):<{widths['no']}}  "
                    f"| {p.get('name', ''):<{widths['name']}}")
        print(row_line)
    # --- 表格化顯示結束 ---

    
    while True:
        try:
            choice_str = input("\n請輸入要操作的專案編號 (或按 Enter 取消) > ").strip()
            if not choice_str: return None
            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(projects):
                return projects[choice_idx]
            else:
                print("無效的編號，請重新輸入。")
        except (ValueError, IndexError):
            print("輸入無效，請輸入列表中的數字編號。")

def _select_field_to_edit() -> Optional[str]:
    """【UX 核心】讓用戶通過數字選擇要修改的欄位。"""
    print("\n--- 請選擇要修改的欄位 ---")
    fields = ['name', 'path', 'output_file']
    for i, field in enumerate(fields):
        print(f"  [{i + 1}] {field}")
    
    while True:
        try:
            choice_str = input("\n請輸入欄位編號 (或按 Enter 取消) > ").strip()
            if not choice_str: return None
            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(fields):
                return fields[choice_idx]
            else:
                print("無效的編號，請重新輸入。")
        except (ValueError, IndexError):
            print("輸入無效，請輸入列表中的數字編號。")
def _display_menu():
    """顯示主菜單 (v5.2 簡潔版)。"""
    print("\n" + "="*50)
    print("      通用目錄哨兵控制中心 v5.2 (UX 畢業版)")
    print("="*50)
    print("  1. 新增專案")
    print("  2. 修改專案")
    print("  3. 刪除專案")
    print(" --- ")
    print("  4. 手動更新 (依名單)")
    print("  5. (調試)自由更新")
    print(" --- 哨兵管理 ---")
    print("  6. 啟動哨兵 (測試)")
    print("  7. 停止哨兵 (測試)")
    print(" --- ")
    print("  9. 測試後端連接 (Ping)")
    print("  0. 退出程序")
    print("="*50)

# --- 主執行區 ---

def main():
    """主循環，包含【原地重試】和【終極安全氣囊】。"""
    while True:
        try:
            _display_menu()
            choice = input("請選擇操作 > ").lower().strip()

            if choice == '0': break
            elif choice == '9': _call_daemon_and_show_feedback(['ping'])
            
            elif choice == '1':
                while True:
                    print("\n--- 新增專案 (輸入 'q' 可隨時返回) ---")
                    name = input("  請輸入專案別名 > ").strip()
                    if name.lower() == 'q': break
                    path = input("  請輸入專案目錄絕對路徑 > ").strip()
                    if path.lower() == 'q': break
                    output_file = input("  請輸入目標 Markdown 文件絕對路徑 > ").strip()
                    if output_file.lower() == 'q': break
                    if name and path and output_file:
                        if _call_daemon_and_show_feedback(['add_project', name, path, output_file]):
                            break
                    else:
                        print("錯誤：所有欄位都必須填寫，請重新輸入。")
            
            elif choice == '2':
                selected_project = _select_project("修改專案")
                if selected_project:
                    uuid = selected_project.get('uuid')
                    name = selected_project.get('name')
                    if uuid:
                        print(f"\n您已選擇專案：'{name}'")
                        field = _select_field_to_edit()
                        if field:
                            new_value = input(f"  請輸入 '{field}' 的新值 > ").strip()
                            if new_value:
                                _call_daemon_and_show_feedback(['edit_project', uuid, field, new_value])
                            else:
                                print("錯誤：新值不能為空。")
                    else:
                        print("錯誤：選中的專案缺少 UUID，無法操作。")

            elif choice == '3':
                selected_project = _select_project("刪除專案")
                if selected_project:
                    uuid = selected_project.get('uuid')
                    name = selected_project.get('name')
                    if uuid:
                        confirm = input(f"\n\033[91m[警告] 您確定要刪除專案 '{name}' 嗎？(輸入 y 確認)\033[0m > ").lower().strip()
                        if confirm == 'y':
                            _call_daemon_and_show_feedback(['delete_project', uuid])
                        else:
                            print("刪除操作已取消。")
                    else:
                        print("錯誤：選中的專案缺少 UUID，無法操作。")

            elif choice == '4':
                selected_project = _select_project("手動更新")
                if selected_project:
                    uuid = selected_project.get('uuid')
                    if uuid:
                        _call_daemon_and_show_feedback(['manual_update', uuid])
                    else:
                        print("錯誤：選中的專案缺少 UUID，無法操作。")

            elif choice == '5':
                print("\n--- (調試)自由更新 ---")
                project_path = input("  請輸入專案目錄絕對路徑 > ").strip()
                target_doc = input("  請輸入目標 Markdown 文件絕對路徑 > ").strip()
                if project_path and target_doc:
                    _call_daemon_and_show_feedback(['manual_direct', project_path, target_doc])
                else:
                    print("錯誤：兩個路徑都必須提供。")

            # 【v5.6 正式版交互】
            # 理由：將「啟動哨兵」，接入標準的、優雅的表格選擇流程。
            elif choice == '6':
                selected_project = _select_project("啟動哨兵")
                if selected_project:
                    uuid = selected_project.get('uuid')
                    if uuid:
                        _call_daemon_and_show_feedback(['start_sentry', uuid])
                    else:
                        print("錯誤：選中的專案缺少 UUID，無法操作。")

            # 【v5.6 正式版交互】
            # 理由：將「停止哨兵」，也接入標準的表格選擇流程。
            elif choice == '7':
                selected_project = _select_project("停止哨兵")
                if selected_project:
                    uuid = selected_project.get('uuid')
                    if uuid:
                        _call_daemon_and_show_feedback(['stop_sentry', uuid])
                    else:
                        print("錯誤：選中的專案缺少 UUID，無法操作。")

            else:
                print(f"無效的選擇 '{choice}'。")

            if choice not in ['0']:
                input("\n--- 按 Enter 鍵返回主菜單 ---")

        except KeyboardInterrupt:
            print("\n\n操作被用戶中斷。正在退出...")
            break
        except Exception as e:
            # 【承諾 3: 終極安全氣囊】
            print("\n" + "="*50)
            print("\033[91m【主程序發生致命錯誤！】\033[0m")
            print("一個未被預料的錯誤導致當前操作失敗，但主程序依然穩定。")
            print("請將以下錯誤信息截圖，以便我們進行分析：")
            print(f"  錯誤類型: {type(e).__name__}")
            print(f"  錯誤詳情: {e}")
            print("="*50)
            input("\n--- 按 Enter 鍵返回主菜單 ---")

if __name__ == "__main__":
    main()
