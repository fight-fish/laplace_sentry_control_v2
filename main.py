# main.py (位於專案根目錄) - 註解重構版

# HACK: 為了讓這個客戶端能獨立運行，我們需要導入一些 Python 內建的標準工具。
# 在未來的純 Python 工作流中，subprocess 將會被移除。
import os
import sys
import time
import json
from io import StringIO
import subprocess

# HACK: 這是解決 Python 中「模組找不到錯誤 (ModuleNotFoundError)」的經典技巧。
# 我們手動將專案的根目錄（project_root）加到系統的「尋找路徑（sys.path）」中，
# 這樣不論我們從哪裡執行這個腳本，它總能找到 src/core/ 下的模組。
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# 我們從源碼（src）的核心（core）中，導入（import）我們唯一的依賴：後端大腦（daemon）。
from src.core import daemon

# --- 輔助顯示函式 (Helper Functions for Display) ---

def clear_screen():
    """一個用來清空終端機畫面的小工具。"""
    # 我們用 os.system 來執行系統命令。如果（if）作業系統是 'nt' (Windows)...
    if os.name == 'nt':
        # ...就執行 'cls' 命令。
        os.system('cls')
    # 否則（else），就執行 'clear' 命令 (適用於 Linux, macOS)。
    else:
        os.system('clear')

def show_main_menu():
    """定義（define）一個專門用來顯示主菜單的函式。"""
    clear_screen()
    print("========================================")
    print("   通用目錄哨兵 - 控制中心 v4.0 (命名升級版)")
    print("========================================")
    print("  [1] 列出所有專案")
    print("  [2] 新增一個專案")
    print("  [3] 修改一個專案")
    print("  [4] 刪除一個專案")
    print("  ------------------------------------")
    # 根據日誌 035 的教訓，這裡的描述必須清晰地區分兩種模式。
    print("  [u]  手動更新 (根據名單選擇專案)")
    print("  [u2] 手動更新 (自由輸入路徑)")
    print("  ------------------------------------")
    print("  [q] 退出系統")
    print("========================================")

# --- 數據獲取與交互輔助函式 (Data Fetching & Interaction Helpers) ---

def _get_projects_from_daemon():
    """
    一個專門負責從後端（daemon）獲取專案列表的內部函式。
    它會捕獲後端的輸出，並將其從 JSON 字串轉換為 Python 的列表。
    """
    # DEFENSE: 為了捕獲 daemon.py 中所有的打印（print）輸出，我們暫時「綁架」了系統的標準輸出（sys.stdout）。
    # 這是個高級技巧，但也容易出錯，所以我們用「try...finally」結構來確保無論如何都能恢復它。
    try:
        old_stdout = sys.stdout
        # 我們創建一個內存中的文字緩衝區（StringIO），並讓所有後續的 print 內容都寫入這裡。
        sys.stdout = captured_output = StringIO()
        # 我們調用（call）後端的「處理列出專案（handle_list_projects）」函式。
        daemon.handle_list_projects()
    # DEFENSE: 我們預期 daemon 函式在執行完後會用 sys.exit() 退出，這會觸發 SystemExit 異常。
    # 我們在這裡把它「接住」並忽略（pass），這是為了讓我們的「綁架」流程能繼續下去。
    except SystemExit:
        pass
    # DEFENSE: 捕獲所有其他可能的意外錯誤。
    except Exception as e:
        # 在報錯前，必須先恢復標準輸出，否則錯誤訊息也會被「綁架」。
        sys.stdout = old_stdout
        print(f"\n【致命錯誤】：在與後台服務通信時發生意外！\n  -> {e}")
        return None
    finally:
        # 「finally」確保這段程式碼無論如何都會被執行，保證我們能「釋放人質」。
        sys.stdout = old_stdout

    # 我們從緩衝區中獲取被捕獲的全部文字內容。
    json_string = captured_output.getvalue()
    # DEFENSE: 後端服務有時可能返回非預期的內容（如錯誤訊息），這會導致 JSON 解析失敗。
    try:
        # 我們嘗試用 json.loads 將文字解析成 Python 物件。
        return json.loads(json_string)
    except json.JSONDecodeError:
        print(f"\n【致命錯誤】：後台服務返回的數據格式不正確。\n  -> 收到的原始數據: {json_string}")
        return None

def select_project_from_list(projects):
    """打印專案列表，並讓使用者通過輸入編號來選擇一個專案。"""
    # DEFENSE: 如果傳入的列表是空的，就直接告知用戶並返回。
    if not projects:
        print("目前沒有任何已註冊的專案。")
        return None

    print("\n編號 | 專案別名             | UUID")
    print("-----|----------------------|---------------------------------------")
    # 我們用「for...in...」這個結構，配合 enumerate 來一個個地處理「專案列表（projects）」。
    for i, p in enumerate(projects, 1):
        # 使用 f-string 和格式化語法，讓輸出像表格一樣對齊。
        print(f"{i:<4} | {p.get('name', 'N/A'):<20} | {p.get('uuid', 'N/A')}")
    print("-----------------------------------------------------------------")

    # 我們用一個「while True」無限循環，來不斷要求用戶輸入，直到得到有效值。
    while True:
        # DEFENSE: 使用 try...except 來處理用戶可能輸入非數字的情況。
        try:
            choice = input("請輸入您想操作的專案編號 (或直接按 Enter 取消): ")
            # 如果用戶直接按 Enter，就取消操作。
            if not choice:
                print("\n操作已取消。")
                return None
            # 將輸入的文字轉換為整數，並減 1 得到索引。
            choice_index = int(choice) - 1
            # 判斷索引是否在有效範圍內。
            if 0 <= choice_index < len(projects):
                # 如果有效，就返回被選中的那個專案物件。
                return projects[choice_index]
            else:
                print("無效的編號，請重新輸入。")
        except ValueError:
            print("輸入無效，請輸入數字。")

# --- 主循環與菜單邏輯 (Main Loop & Menu Logic) ---

def main():
    """程式的主循環，負責接收用戶輸入並調度功能。"""
    while True:
        show_main_menu()
        # 我們獲取用戶輸入，並用 lower() 轉為小寫，用 strip() 去掉頭尾空格，以增加容錯性。
        choice = input("請輸入您的選擇: ").lower().strip()

        if choice == '1': # 列出專案
            clear_screen()
            print("--- 所有已註冊的專案 ---")
            projects = _get_projects_from_daemon()
            # 如果成功獲取到專案列表...
            if projects:
                print("\n編號 | 專案別名             | UUID")
                print("-----|----------------------|---------------------------------------")
                for i, p in enumerate(projects, 1):
                    print(f"{i:<4} | {p.get('name', 'N/A'):<20} | {p.get('uuid', 'N/A')}")
                print("-----------------------------------------------------------------")
            # 如果獲取到的是一個空列表...
            elif projects is not None:
                print("目前沒有任何已註冊的專案。")
            # 如果獲取失敗 (為 None)，_get_projects_from_daemon 內部已經打印了錯誤。
            input("\n按 Enter 鍵返回主菜單...")

        elif choice == '2': # 新增專案
            clear_screen()
            print("--- 新增專案 ---")
            # DEFENSE: 捕獲後端可能拋出的 SystemExit 或其他異常。
            try:
                name = input("請輸入專案別名: ").strip()
                if not name:
                    print("\n操作取消：專案別名不能為空。")
                else:
                    path = input("請輸入要監控的專案目錄路徑: ").strip()
                    output_file = input("請輸入要更新的 Markdown 檔案路徑: ").strip()
                    # 我們將所有參數打包成一個列表（list）。
                    args_list = [name, path, output_file]
                    print("\n  > 正在將請求發送至後台服務...")
                    # 我們直接調用後端函式，並將參數列表傳給它。
                    daemon.handle_add_project(args_list)
            except SystemExit as e:
                # 我們通過後端返回的「退出碼（exit code）」來判斷操作是否成功。
                if e.code == 0:
                    print("\n✅ 後台服務回覆：成功新增專案！")
                else:
                    print("\n❌ 新增失敗，請檢查後台報告。")
            except Exception as e:
                print(f"\n【致命錯誤】：{e}")
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
                    # 我們用一個字典（dict）來映射用戶的選擇和真實的欄位名。
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
                        else:
                            print("\n操作取消：新值不能為空。")
                    else:
                        print("\n無效的選擇，操作已取消。")
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
                    # DEFENSE: 這是「二次確認安全鎖」，防止用戶誤刪。
                    print("\n" + "="*40 + f"\n  ⚠️  警告：您即將永久刪除專案 '{name_to_delete}'！\n" + "="*40)
                    confirmation = input(f"請再次輸入完整的專案名稱 '{name_to_delete}' 以確認刪除: ").strip()
                    # 只有當用戶輸入的內容和專案名完全一樣時，才執行刪除。
                    if confirmation == name_to_delete:
                        args_list = [uuid_to_delete]
                        print("\n  > 正在將請求發送至後台服務...")
                        try:
                            daemon.handle_delete_project(args_list)
                        except SystemExit as e:
                            if e.code == 0: print("\n✅ 後台服務回覆：成功刪除專案！")
                            else: print("\n❌ 刪除失敗，請檢查後台報告。")
                        except Exception as e: print(f"\n【致命錯誤】：{e}")
                    else:
                        print("\n輸入不匹配，刪除操作已安全取消。")
            input("\n按 Enter 鍵返回主菜單...")

        elif choice == 'u':  # 依名單手動更新
            clear_screen()
            print("--- 手動更新 (根據名單) ---")
            projects = _get_projects_from_daemon()
            if projects is None:
                input("\n(發生錯誤) 按 Enter 返回主選單...")
                continue # continue 會跳過本次循環的剩餘部分，直接開始下一次循環。
            
            selected_project = select_project_from_list(projects)
            if not selected_project:
                input("\n按 Enter 返回主選單...")
                continue

            chosen_uuid = selected_project.get('uuid', '').strip()
            chosen_name = selected_project.get('name', '<未命名>')
            
            print(f"\n> 正在依名單手動更新：{chosen_name}")
            # HACK: 這裡我們用 subprocess.call 來執行一個全新的 Python 進程，
            # 調用 daemon.py 並傳遞 'manual_update' 指令。
            # 這是因為更新流程可能很長，我們不希望它阻塞主菜單。
            # TODO: 在未來實現全 Python 工作流後，這裡應該改為直接調用 daemon 內的函式。
            exit_code = subprocess.call([sys.executable, "src/core/daemon.py", "manual_update", chosen_uuid])

            if exit_code == 0:
                print("✅ 更新完成。")
            else:
                print("❌ 更新失敗，請查看後台輸出。")
            input("\n按 Enter 鍵返回主菜單...")

        elif choice == 'u2': # 自由手動更新
            clear_screen()
            print("--- 手動更新 (自由輸入路徑) ---")
            print("此模式將繞開所有已註冊的專案名單，直接對您提供的路徑執行一次更新。")
            project_path = input("\n請輸入專案資料夾的絕對路徑：").strip()
            target_doc = input("請輸入目標檔案 (markdown) 的絕對路徑：").strip()

            # HACK: 同上，這裡也是通過創建一個全新的進程來執行任務。
            # TODO: 在未來實現全 Python 工作流後，這裡應該改為直接調用 daemon 內的函式。
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
            # time.sleep 讓程式暫停 1.5 秒，給用戶時間看清錯誤提示。
            time.sleep(1.5)

# 這是一個 Python 的標準寫法。
# 它確保只有當這個文件被直接執行時（而不是被當作模組導入時），main() 函式才會被調用。
if __name__ == "__main__":
    main()
