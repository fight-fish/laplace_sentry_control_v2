# tests/test_worker_workflow.py

# 我們需要 導入（import）一系列 Python 內建的工具。
import unittest
import os
import shutil
import sys
import subprocess

# 我們用「class」關鍵字，來定義一個我們自己的「測試案例集」。
# 它 繼承（inherits from）自 unittest.TestCase，這意味著它擁有執行測試的能力。
class TestWorkerWorkflow(unittest.TestCase):

    # 我們用「def setUp」來定義一個「測試前準備」的函式。
    # 在每一個測試函式執行前，這個函式都會被自動調用一次。
    def setUp(self):
        """為每個測試創建一個乾淨的、臨時的測試環境。"""
        # 我們定義一個臨時目錄的名稱。
        self.test_dir = "temp_test_project_for_worker"
        # 我們檢查這個目錄是否已經存在（例如，上次測試失敗後遺留的）。
        if os.path.exists(self.test_dir):
            # 如果存在，就用 shutil.rmtree 強制刪除它和它裡面的所有內容。
            shutil.rmtree(self.test_dir)
        
        # 我們創建這個全新的、乾淨的臨時目錄。
        os.makedirs(self.test_dir)
        # 我們在臨時目錄下，再創建一個子目錄。
        os.makedirs(os.path.join(self.test_dir, "src"))
        # 我們在臨時目錄下，創建一個空的檔案。
        with open(os.path.join(self.test_dir, "README.md"), "w") as f:
            f.write("This is a test readme.")
        # 我們在子目錄下，也創建一個檔案。
        with open(os.path.join(self.test_dir, "src", "main.py"), "w") as f:
            f.write("print('hello')")

    # 我們用「def tearDown」來定義一個「測試後清理」的函式。
    # 在每一個測試函式執行後，這個函式都會被自動調用一次。
    def tearDown(self):
        """在每個測試結束後，清理掉測試環境。"""
        # 我們再次檢查臨時目錄是否存在。
        if os.path.exists(self.test_dir):
            # 如果存在，就刪除它，確保不留下任何測試垃圾。
            shutil.rmtree(self.test_dir)

    # 我們用「def test_...」來定義一個真正的測試函式。
    # 它的名字必須以「test_」開頭。
    def test_current_subprocess_workflow(self):
        """
        【黃金標準測試 v2 - 動態生成版】
        本測試旨在 100% 復現並驗證當前 worker.py 通過 subprocess 運行的正確行為。
        它通過直接調用底層專家來動態生成「黃金標準」，從而避免手動編寫預期結果時的空格和排序錯誤。
        """
        # --- 1. 準備 (Arrange) ---
        worker_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'core', 'worker.py'))
        project_path = self.test_dir
        old_content = ""

        # --- 1a. 動態生成「黃金標準」 (The Golden Standard) ---
        # HACK: 為了能導入 src/core 下的模塊，我們臨時將專案根目錄添加到系統路徑中。
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.core import engine, formatter
        from io import StringIO

        # 我們直接調用 engine 的函式，生成「原材料」。
        raw_material = engine.generate_annotated_tree(project_path, old_content)
        
        # 我們創建一個假的「標準輸入」，把「原材料」放進去。
        fake_stdin = StringIO(raw_material)
        # 我們創建一個假的「標準輸出」，用來捕獲結果。
        fake_stdout = StringIO()

        # 我們創建一個假的「命令行參數列表」。
        # 列表的第一個元素通常是腳本名本身，但 argparse 不關心它，所以可以是任意字串。
        # 關鍵是後面的參數，必須和 worker.py 中調用時完全一致。
        fake_argv = ['formatter.py', '--strategy', 'obsidian']

        # 我們用一個 try...finally 結構來確保無論發生什麼，都能恢復原始的系統狀態。
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        original_argv = sys.argv # <--- 新增：備份原始的 sys.argv
        try:
            # 我們用「猴子補丁」的技巧，暫時「劫持」系統的三大核心組件。
            sys.stdin = fake_stdin
            sys.stdout = fake_stdout
            sys.argv = fake_argv # <--- 新增：劫持 sys.argv
            
            # 我們調用 formatter 的 main() 函式。
            # 現在，它會從我們偽造的 stdin 讀取，向我們偽造的 stdout 寫入，
            # 並從我們偽造的 argv 解析參數。它完全活在我們為它創建的「矩陣」裡。
            formatter.main()
            
            # 我們從偽造的 stdout 中獲取 formatter 處理後的結果。
            expected_output = fake_stdout.getvalue()
        finally:
            # 無論成功還是失敗，都必須把原始的系統狀態還原回去！
            sys.stdin = original_stdin
            sys.stdout = original_stdout
            sys.argv = original_argv # <--- 新增：還原 sys.argv



        # --- 2. 執行 (Act) ---
        # 我們像之前一樣，通過 subprocess 執行完整的 worker.py 工作流。
        result = subprocess.run(
            [sys.executable, worker_script_path, project_path, "-"],
            input=old_content,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False
        )

        # --- 3. 斷言 (Assert) ---
        # 我們斷言返回碼為 0。
        self.assertEqual(result.returncode, 0, f"工人腳本執行失敗，錯誤報告:\n{result.stderr}")
        
        # 我們斷言，通過 subprocess 執行的「現實」，與我們直接調用內部函式生成的「黃金標準」，完全一致。
        self.assertEqual(result.stdout.strip(), expected_output.strip())

    # 我們用「def test_...」來定義一個全新的測試函式。
    def test_workflow_with_ignore_patterns(self):
        """
        【TDD 測試】
        本測試旨在驗證改造後的 worker.py，能否正確接收 ignore_patterns 參數，
        並將其成功傳遞給底層的 engine.py，以實現目錄過濾。
        """
        # --- 1. 準備 (Arrange) ---
        # 我們在現有的測試環境基礎上，額外創建一個應該被忽略的目錄。
        os.makedirs(os.path.join(self.test_dir, "node_modules"))
        with open(os.path.join(self.test_dir, "node_modules", "some_lib.js"), "w") as f:
            f.write("/* some library */")

        # 我們定義一個「忽略規則集」。
        ignore_set = {'node_modules'}
        
        # 我們準備好 worker.py 的其他常規參數。
        project_path = self.test_dir
        old_content = ""

        # --- 1a. 動態生成「黃金標準」 (帶有忽略規則) ---
        # HACK: 再次使用路徑技巧來導入我們的專家。
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.core import engine, formatter
        from io import StringIO

        # 關鍵區別：我們在調用 engine 時，傳入了我們定義的 ignore_set。
        # 因此，這個「原材料」從一開始就應該不包含 node_modules。
        raw_material = engine.generate_annotated_tree(
            project_path, 
            old_content,
            ignore_patterns=ignore_set # <--- 將忽略規則傳入
        )
        
        # 後續的打包流程與之前相同。
        fake_stdin = StringIO(raw_material)
        fake_stdout = StringIO()
        fake_argv = ['formatter.py', '--strategy', 'obsidian']
        original_stdin, original_stdout, original_argv = sys.stdin, sys.stdout, sys.argv
        try:
            sys.stdin, sys.stdout, sys.argv = fake_stdin, fake_stdout, fake_argv
            formatter.main()
            expected_output = fake_stdout.getvalue()
        finally:
            sys.stdin, sys.stdout, sys.argv = original_stdin, original_stdout, original_argv

        # --- 2. 執行 (Act) ---
        # 我們導入 worker 專家。
        from src.core import worker
        
        # 我們調用 worker 的主函式，並嘗試傳入新的 ignore_patterns 參數。
        # 因為 worker.py 現在還不認識這個參數，所以這一步預期會拋出 TypeError。
        exit_code, result = worker.execute_update_workflow(
            project_path, 
            "", # target_doc 在這個純 Python 調用中已無實際作用，但需佔位。
            old_content,
            ignore_patterns=ignore_set # <--- 嘗試傳入新參數
        )

        # --- 3. 斷言 (Assert) ---
        self.assertEqual(exit_code, 0, f"工人腳本執行失敗，錯誤報告:\n{result}")
        self.assertEqual(result.strip(), expected_output.strip())

# 這是一個 Python 的標準寫法。
# 它確保只有當這個文件被直接執行時，下面的程式碼才會被運行。
if __name__ == '__main__':
    # unittest.main() 會自動發現這個文件裡所有以「test_」開頭的函式，並執行它們。
    unittest.main()

