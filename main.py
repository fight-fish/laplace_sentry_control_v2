# main.py (位於專案根目錄) - 最終正確版 v3.7

# 我們需要的標準工具
import os
import sys
import time
import json
from io import StringIO
import subprocess # 【v3.7】為了手動模式調用外部腳本

# 我們需要定義根目錄，並將其加入搜索路徑
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# main.py 唯一的依賴，就是 daemon
from src.core import daemon

# --- 輔助顯示函式 ---

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_main_menu():
    clear_screen()
    print("========================================")
    print("   通用目錄哨兵 - 控制中心 v4.0 (命名升級版)") 
    print("========================================")
    print("  [1] 列出所有專案")
    print("  [2] 新增一個專案")
    print("  [3] 修改一個專案")
    print("  [4] 刪除一個專案")
    print("  ------------------------------------")
    # 【核心修正 1】'u' 模式的描述，強調它是基於「名單」的
    print("  [u]  手動更新 (根據名單選擇專案)")
    # 【核心修正 2】'u2' 模式的描述，強調它是「自由輸入」的
    print("  [u2] 手動更新 (自由輸入路徑)")
    print("  ------------------------------------")
    print("  [q] 退出系統")
    print("========================================")



# --- 數據獲取與交互輔助函式 ---

def _get_projects_from_daemon():
    """專門負責從 daemon 獲取數據並返回 Python 列表。"""
    try:
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        daemon.handle_list_projects()
    except SystemExit: pass
    except Exception as e:
        sys.stdout = old_stdout
        print(f"\n【致命錯誤】：在與後台服務通信時發生意外！\n  -> {e}")
        return None
    finally:
        sys.stdout = old_stdout
    
    json_string = captured_output.getvalue()
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        print(f"\n【致命錯誤】：後台服務返回的數據格式不正確。\n  -> 收到的原始數據: {json_string}")
        return None

def select_project_from_list(projects):
    """打印列表並讓使用者從中選擇一個專案。"""
    if not projects:
        print("目前沒有任何已註冊的專案。")
        return None

    print("\n編號 | 專案別名             | UUID")
    print("-----|----------------------|---------------------------------------")
    for i, p in enumerate(projects, 1):
        print(f"{i:<4} | {p.get('name', 'N/A'):<20} | {p.get('uuid', 'N/A')}")
    print("-----------------------------------------------------------------")
    
    while True:
        try:
            choice = input("請輸入您想操作的專案編號 (或直接按 Enter 取消): ")
            if not choice:
                print("\n操作已取消。")
                return None
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(projects):
                return projects[choice_index]
            else:
                print("無效的編號，請重新輸入。")
        except ValueError:
            print("輸入無效，請輸入數字。")

# --- 【v3.7 核心修正】手動更新模式的最終正確實現 ---

# 請用以下完整的函式，替換掉 main.py 中舊的 manual_update_menu 函式

def manual_update_menu():
    """
    【v3.8 嚴格模式版】
    此函式是完全獨立的「終極調試工具」。
    當目標文件不存在時，它必須報告錯誤並中止，而不是自動創建。
    """
    clear_screen()
    print("--- 手動執行一次更新 (終極調試工具) ---")
    print("此模式將繞開所有已註冊的專案名單，直接對您提供的路徑執行一次更新。")
    
    project_path = input("\n請輸入要掃描的【專案目錄】路徑: ").strip()
    if not project_path:
        print("\n操作取消：專案目錄路徑不能為空。")
        return

    target_doc_path = input("請輸入要寫入的【目標文件】路徑: ").strip()
    if not target_doc_path:
        print("\n操作取消：目標文件路徑不能為空。")
        return

    print(f"\n您已指定：")
    print(f"  - 掃描目標: {project_path}")
    print(f"  - 輸出文件: {target_doc_path}")
    
    try:
        # 1. 直接調用 path.py read 命令，讀取舊內容
        print("\n  > [1/3] 正在直接調用路徑專家 (path.py) 讀取舊文件內容...")
        path_script_path = os.path.join(project_root, 'src', 'core', 'path.py')
        read_process = subprocess.run(
            [sys.executable, path_script_path, 'read', target_doc_path],
            capture_output=True, text=True, encoding='utf-8'
        )
        
        # 【v3.8 核心修正】回歸嚴格模式：只要讀取失敗，就立刻中止！
        if read_process.returncode != 0:
            print(f"\n❌ 讀取文件失敗！路徑專家報告：\n{read_process.stderr}")
            return
        
        # 只有在讀取成功時，才將內容賦值給 old_content
        old_content = read_process.stdout
        # 2. 直接調用 worker.sh，並通過管道傳遞舊內容
        print("  > [2/3] 正在直接調用工人腳本 (worker.sh) 執行核心更新流程...")
        worker_script_path = os.path.join(project_root, 'src', 'shell', 'worker.sh')
        
        # 【v3.9 終極環境修正】
        # 我們在調用子進程時，必須明確地將當前 Python 腳本的【完整環境變數】
        # 傳遞給它！這樣才能確保 worker.sh 能找到像 python3 這樣的核心命令。
        worker_process = subprocess.run(
            ['bash', worker_script_path, project_path, target_doc_path],
            input=old_content, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            env=os.environ  # <--- 唯一的、決定成敗的修正！
        )

        # 3. 分析工人腳本的執行結果
        print("  > [3/3] 正在分析工人腳本的執行結果...")
        if worker_process.returncode == 0:
            print("\n✅ 工人腳本報告：更新成功完成！")
            if worker_process.stdout:
                print("\n--- 工人腳本輸出 (stdout) ---\n" + worker_process.stdout)
        else:
            print("\n❌ 工人腳本報告：執行失敗！")
            if worker_process.stderr:
                print("\n--- 工人腳本錯誤 (stderr) ---\n" + worker_process.stderr)

    except FileNotFoundError as e:
        print(f"\n❌ 致命錯誤：找不到依賴的腳本（如 'worker.sh' 或 'path.py'）。\n  -> {e}")
    except Exception as e:
        print(f"\n❌ 致命錯誤：在執行手動更新時發生意外！\n  -> {e}")

        input("\n(已完成) 按 Enter 返回主選單...")

# --- 主循環與其他菜單邏輯 ---

def main():
    """程式的主循環，負責接收用戶輸入並調度功能。"""
    while True:
        show_main_menu()
        choice = input("請輸入您的選擇: ").lower().strip()

        if choice == '1':
            clear_screen()
            print("--- 所有已註冊的專案 ---")
            projects = _get_projects_from_daemon()
            if projects:
                print("\n編號 | 專案別名             | UUID")
                print("-----|----------------------|---------------------------------------")
                for i, p in enumerate(projects, 1):
                    print(f"{i:<4} | {p.get('name', 'N/A'):<20} | {p.get('uuid', 'N/A')}")
                print("-----------------------------------------------------------------")
            elif projects is not None:
                print("目前沒有任何已註冊的專案。")
            input("\n按 Enter 鍵返回主菜單...")

        elif choice == '2': # 新增專案
            clear_screen()
            print("--- 新增專案 ---")
            try:
                name = input("請輸入專案別名: ").strip()
                if not name:
                    print("\n操作取消：專案別名不能為空。")
                else:
                    path = input("請輸入要監控的專案目錄路徑: ").strip()
                    output_file = input("請輸入要更新的 Markdown 檔案路徑: ").strip()
                    args_list = [name, path, output_file]
                    print("\n  > 正在將請求發送至後台服務...")
                    daemon.handle_add_project(args_list)
            except SystemExit as e:
                if e.code == 0: print("\n✅ 後台服務回覆：成功新增專案！")
                else: print("\n❌ 新增失敗，請檢查後台報告。")
            except Exception as e: print(f"\n【致命錯誤】：{e}")
            input("\n按 Enter 鍵返回主菜單...")

        elif choice == '3': # 修改專案
            clear_screen()
            print("--- 修改專案 ---")
            projects = _get_projects_from_daemon()
            if projects is not None:
                selected_project = select_project_from_list(projects)
                if selected_project:
                    uuid_to_edit = selected_project['uuid']
                    print(f"\n您已選擇修改專案: '{selected_project['name']}'")
                    print("您可以修改以下哪個欄位？\n  [1] 專案別名 (name)\n  [2] 專案路徑 (path)\n  [3] 輸出文件 (output_file)")
                    field_choice = input("請輸入您的選擇: ").strip()
                    field_map = {'1': 'name', '2': 'path', '3': 'output_file'}
                    if field_choice in field_map:
                        field_to_edit = field_map[field_choice]
                        new_value = input(f"請輸入 '{field_to_edit}' 的新值: ").strip()
                        if new_value:
                            args_list = [uuid_to_edit, field_to_edit, new_value]
                            print("\n  > 正在將請求發送至後台服務...")
                            try:
                                daemon.handle_edit_project(args_list)
                            except SystemExit as e:
                                if e.code == 0: print("\n✅ 後台服務回覆：成功修改專案！")
                                else: print("\n❌ 修改失敗，請檢查後台報告。")
                            except Exception as e: print(f"\n【致命錯誤】：{e}")
                        else: print("\n操作取消：新值不能為空。")
                    else: print("\n無效的選擇，操作已取消。")
            input("\n按 Enter 鍵返回主菜單...")

        elif choice == '4': # 刪除專案
            clear_screen()
            print("--- 刪除專案 ---")
            projects = _get_projects_from_daemon()
            if projects is not None:
                selected_project = select_project_from_list(projects)
                if selected_project:
                    uuid_to_delete = selected_project['uuid']
                    name_to_delete = selected_project['name']
                    print("\n" + "="*40 + f"\n  ⚠️  警告：您即將永久刪除專案 '{name_to_delete}'！\n" + "="*40)
                    confirmation = input(f"請再次輸入完整的專案名稱 '{name_to_delete}' 以確認刪除: ").strip()
                    if confirmation == name_to_delete:
                        args_list = [uuid_to_delete]
                        print("\n  > 正在將請求發送至後台服務...")
                        try:
                            daemon.handle_delete_project(args_list)
                        except SystemExit as e:
                            if e.code == 0: print("\n✅ 後台服務回覆：成功刪除專案！")
                            else: print("\n❌ 刪除失敗，請檢查後台報告。")
                        except Exception as e: print(f"\n【致命錯誤】：{e}")
                    else: print("\n輸入不匹配，刪除操作已安全取消。")
            input("\n按 Enter 鍵返回主菜單...")

        elif choice == 'u':  # 依名單手動更新：列出名單 -> 選一個 -> 更新該 UUID
            clear_screen()
            print("--- 已註冊的專案名單 ---")

            projects = _get_projects_from_daemon()
            if projects is None:
                input("\n(發生錯誤) 按 Enter 返回主選單...")
                continue
            if not projects:
                print("目前沒有任何已註冊的專案。")
                input("\n按 Enter 返回主選單...")
                continue

            # 顯示列表並讓使用者選擇
            selected_project = select_project_from_list(projects)
            if not selected_project:
                input("\n按 Enter 返回主選單...")
                continue

            chosen_uuid = selected_project.get('uuid', '').strip()
            chosen_name = selected_project.get('name', '<未命名>')
            if not chosen_uuid:
                print("【錯誤】：該專案缺少 UUID，無法進行手動更新。")
                input("\n按 Enter 返回主選單...")
                continue

            print(f"\n> 正在依名單手動更新：{chosen_name}")
            proc = subprocess.run([sys.executable, "src/core/daemon.py", "manual_update", chosen_uuid],
                                capture_output=True, text=True, encoding='utf-8')
            if proc.stdout:
                print(proc.stdout)
            if proc.returncode == 0:
                print("✅ 更新完成。")
            else:
                if proc.stderr:
                    print("\n--- 後台報告 (daemon stderr) ---")
                    print(proc.stderr)
                print("❌ 更新失敗。請依上方錯誤訊息修正後再試。")
            input("\n按 Enter 鍵返回主菜單.")




        elif choice.upper() == 'U2':
            print("\n🧩 自由手動更新模式")
            project_path = input("請輸入專案資料夾的絕對路徑：").strip()
            target_doc = input("請輸入目標檔案 (markdown) 的絕對路徑：").strip()

            subprocess.run([
                sys.executable, "src/core/daemon.py", "manual_direct",
                project_path, target_doc
            ])

            input("\n(已完成) 按 Enter 返回主選單...")

        elif choice == 'q':
            print("\n正在退出系統，感謝使用！")
            sys.exit(0)

        else:
            print(f"\n無效的選擇「{choice}」，請重新輸入。")
            time.sleep(1.5)

if __name__ == "__main__":
    main()
