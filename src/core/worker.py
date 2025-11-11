# src/core/worker.py

# 我們需要 導入（import）一系列 Python 內建的工具。
import os
import sys
from io import StringIO
# 我們從 typing 導入 Optional，因為新參數是可選的。
from typing import Optional, Set

# HACK: 這段程式碼是為了解決一個導入問題。
# 我們用「if __name__ == '__main__'」這個結構來判斷，如果（if）這個腳本是直接被執行的...
if __name__ == '__main__' and __package__ is None:
    # 我們就獲取當前腳本所在的目錄路徑。
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 然後獲取上上級目錄，也就是我們整個專案的根目錄。
    project_root = os.path.dirname(os.path.dirname(current_dir))
    # 最後，我們把這個根目錄，插入（insert）到系統的「尋找路徑列表（sys.path）」的最前面。
    sys.path.insert(0, project_root)

# --- 【v2.0 核心重構】 ---
# 我們現在不再需要 subprocess，而是直接導入我們的專家模塊。
from src.core import engine, formatter

# 我們用「def」來 定義（define）一個我們自己的函式，名為「執行更新工作流」。
def execute_update_workflow(
    project_path: str, 
    target_doc: str, 
    old_content: str, 
    ignore_patterns: Optional[Set[str]] = None  # <--- 核心改造點 1
) -> tuple[int, str]:    
    """
    【工人專家 v2.0 - 純 Python 版】
    執行完整的「生產->包裝」更新流水線，所有專家均通過內部函式調用。
    """
    try:
        # --- 步驟 1: 直接調用 engine.py (生產線) ---
        # 我們在調用 engine 時，將接收到的 ignore_patterns 參數原封不動地傳遞下去。
        raw_material = engine.generate_annotated_tree(
            project_path, 
            old_content,
            ignore_patterns=ignore_patterns # <--- 核心改造點 2
        )

        # --- 步驟 2: 直接調用 formatter.py (包裝線) ---
        # 我們使用在測試中被驗證過的「環境偽造」技巧，來安全地調用 formatter.main()。
        fake_stdin = StringIO(raw_material)
        fake_stdout = StringIO()
        # 我們偽造一個符合 formatter 預期的命令行參數列表。
        fake_argv = ['formatter.py', '--strategy', 'obsidian']

        # 我們備份並劫持系統的 I/O 和參數。
        original_stdin, original_stdout, original_argv = sys.stdin, sys.stdout, sys.argv
        try:
            sys.stdin, sys.stdout, sys.argv = fake_stdin, fake_stdout, fake_argv
            # 在這個安全的「矩陣」中，執行 formatter 的 main 函式。
            formatter.main()
            # 從偽造的標準輸出中，獲取最終的「成品」。
            finished_product = fake_stdout.getvalue()
        finally:
            # 無論如何，都必須將系統狀態還原！
            sys.stdin, sys.stdout, sys.argv = original_stdin, original_stdout, original_argv
        
        # 所有步驟都順利完成，我們 返回（return）一個代表成功的退出碼 `0` 和我們的最終成品。
        return (0, finished_product.strip())

    # 我們用一個全局的「except Exception」來捕獲任何在工作流中可能發生的未知錯誤。
    except Exception as e:
        # 如果發生任何錯誤，我們就準備一份詳細的錯誤報告。
        error_message = f"【工人失敗 v2.0】：在純 Python 工作流中發生意外錯誤。\n--- 錯誤詳情 ---\n{type(e).__name__}: {e}"
        # 然後，返回（return）一個代表失敗的退出碼 `3` 和這份錯誤報告。
        return (3, error_message)


# 我們用「if __name__ == '__main__'」這個結構來判斷，如果（if）這個腳本是直接被執行的...
# TAG: COMPAT (相容性)
# 我們保留這個 main 區塊，是為了確保即使有其他舊腳本試圖通過命令行調用它，它依然能工作。
# 但在我們的新架構中，這個區塊實際上已經不會被 daemon.py 調用了。
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python worker.py <project_path> <target_doc>", file=sys.stderr)
        sys.exit(1)
    
    project_path_arg = sys.argv[1]
    target_doc_arg = sys.argv[2]
    old_content_arg = sys.stdin.read()
    
    exit_code, result = execute_update_workflow(project_path_arg, target_doc_arg, old_content_arg)
    
    if exit_code == 0:
        print(result)
    else:
        print(result, file=sys.stderr)
        
    sys.exit(exit_code)
