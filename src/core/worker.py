# 我們需要 導入（import）幾個 Python 內建的標準工具。
import os
import sys
import subprocess

# HACK: 這段程式碼是為了解決一個導入問題。
# 我們用「if __name__ == '__main__'」這個結構來判斷，如果（if）這個腳本是直接被執行的...
if __name__ == '__main__' and __package__ is None:
    # 我們就獲取當前腳本所在的目錄路徑。
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 然後獲取上上級目錄，也就是我們整個專案的根目錄。
    project_root = os.path.dirname(os.path.dirname(current_dir))
    # 最後，我們把這個根目錄，插入（insert）到系統的「尋找路徑列表（sys.path）」的最前面。
    sys.path.insert(0, project_root)

# 我們用「def」來 定義（define）一個我們自己的函式，名為「執行更新工作流」。
# 它會返回一個「元組（tuple）」，裡面包含一個整數和一個字串。
def execute_update_workflow(project_path: str, target_doc: str, old_content: str) -> tuple[int, str]:
    """
    【工人專家】執行完整的「生產->包裝」更新流水線。
    """
    # 我們先獲取專案的根目錄路徑。
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # --- 步驟 1: 調用 engine.py (生產線) ---
    # 我們把「結構專家（engine.py）」的完整路徑準備好。
    engine_script_path = os.path.join(project_root, 'src', 'core', 'engine.py')
    # 我們用「subprocess.run」這個工具，來執行一個外部命令。
    p1 = subprocess.run(
        # 這個命令被打包成一個「列表（list）」。
        [sys.executable, engine_script_path, project_path, "-"],
        input=old_content,
        text=True,
        encoding='utf-8',
        capture_output=True,
        env=os.environ
    )
    # 我們用「if」來判斷，如果（if）上一步操作的「返回碼（returncode）」不等於 0...
    if p1.returncode != 0:
        # 我們就準備一份錯誤報告。
        error_message = f"【工人失敗】：結構專家 (engine.py) 執行失敗。\n--- 結構專家錯誤報告 ---\n{p1.stderr.strip()}"
        # 然後，我們 返回（return）一個代表失敗的退出碼 `3` 和這份錯誤報告。
        return (3, error_message)

    # 如果成功，我們就把專家產出的「原材料」保存下來。
    raw_material = p1.stdout

    # --- 步驟 2: 調用 formatter.py (包裝線) ---
    # 我們準備好「格式化專家（formatter.py）」的完整路徑。
    formatter_script_path = os.path.join(project_root, 'src', 'core', 'formatter.py')
    # 我們再次用「subprocess.run」來執行命令。
    p2 = subprocess.run(
        [sys.executable, formatter_script_path, "--strategy", "obsidian"],
        input=raw_material,
        text=True,
        encoding='utf-8',
        capture_output=True,
        env=os.environ
    )
    # 我們再次用「if」來判斷返回碼。
    if p2.returncode != 0:
        # 如果失敗，就準備另一份錯誤報告。
        error_message = f"【工人失敗】：格式化專家 (formatter.py) 執行失敗。\n--- 格式化專家錯誤報告 ---\n{p2.stderr.strip()}"
        # 然後，返回（return）失敗碼 `3` 和錯誤報告。
        return (3, error_message)

    # 如果成功，我們就得到了最終的「成品」。
    finished_product = p2.stdout
    
    # 所有步驟都順利完成，我們 返回（return）一個代表成功的退出碼 `0` 和我們的最終成品。
    return (0, finished_product)

# 我們用「if __name__ == '__main__'」這個結構來判斷，如果（if）這個腳本是直接被執行的...
if __name__ == '__main__':
    # 我們用「if」來判斷，如果（if）傳入的參數數量不等於 3...
    if len(sys.argv) != 3:
        # 我們就用「print」在「標準錯誤（stderr）」中打印用法說明。
        print("用法: python worker.py <project_path> <target_doc>", file=sys.stderr)
        # 然後用「sys.exit」以失敗碼 `1` 退出腳本。
        sys.exit(1)
    
    # 我們從「系統參數列表（sys.argv）」中獲取參數。
    project_path_arg = sys.argv[1]
    target_doc_arg = sys.argv[2]
    # 我們從「標準輸入（stdin）」中 讀取（read）所有內容。
    old_content_arg = sys.stdin.read()
    
    # 我們調用我們的主要函式來執行工作流。
    exit_code, result = execute_update_workflow(project_path_arg, target_doc_arg, old_content_arg)
    
    # 我們用「if」來判斷工作流是否成功。
    if exit_code == 0:
        # 如果成功，就用「print」把結果打印到「標準輸出（stdout）」。
        print(result)
    # 否則（else）...
    else:
        # 就用「print」把錯誤報告打印到「標準錯誤（stderr）」。
        print(result, file=sys.stderr)
        
    # 最後，我們用「sys.exit」以工作流返回的「退出碼」來退出整個腳本。
    sys.exit(exit_code)
