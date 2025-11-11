# tests/test_daemon_integration.py

import unittest
import os
import shutil
import sys
from typing import List, Dict, Any

# HACK: 為了能導入 src/core 下的模塊，我們臨時將專案根目錄添加到系統路徑中。
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 我們導入這次測試的主角：daemon
from src.core import daemon

class TestDaemonIntegration(unittest.TestCase):

    def setUp(self):
        """為每個測試創建一個乾淨的、臨時的測試環境。"""
        self.test_dir = "temp_test_project_for_daemon"
        self.target_md_file = os.path.join(self.test_dir, "TARGET.md")
        
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        
        os.makedirs(self.test_dir)
        os.makedirs(os.path.join(self.test_dir, "src"))
        os.makedirs(os.path.join(self.test_dir, "node_modules")) # 為了測試忽略規則

        with open(os.path.join(self.test_dir, "src", "main.py"), "w") as f:
            f.write("print('hello')")
        with open(os.path.join(self.test_dir, "node_modules", "lib.js"), "w") as f:
            f.write("/* lib */")
        with open(self.target_md_file, "w") as f:
            f.write("Initial content.")

    def tearDown(self):
        """在每個測試結束後，清理掉測試環境。"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_update_workflow_with_ignore_patterns(self):
        """
        【最終驗收測試】
        驗證 daemon 的完整更新工作流，在接收到 ignore_patterns 參數後，
        能否正確地生成一個已過濾的目錄樹，並將其寫入目標文件。
        """
        # --- 1. 準備 (Arrange) ---
        # 我們使用 os.path.abspath() 來確保傳遞給 daemon 的是絕對路徑。
        project_path = os.path.abspath(self.test_dir)
        target_doc = os.path.abspath(self.target_md_file)
        ignore_set = {'node_modules'}
        
        initial_md_content = "Some content before.\n<!-- AUTO_TREE_START -->\nold tree\n<!-- AUTO_TREE_END -->\nSome content after."
        with open(target_doc, "w", encoding="utf-8") as f:
            f.write(initial_md_content)

        # --- 2. 執行 (Act) ---
        # 我們直接調用改造後的 daemon 函式。
        daemon.handle_manual_direct([project_path, target_doc], ignore_patterns=ignore_set)

        # --- 3. 斷言 (Assert) ---
        # 我們讀取被 daemon 更新後的目標文件的最終內容。
        with open(target_doc, "r", encoding="utf-8") as f:
            final_content = f.read()

        # 我們斷言，最終的內容中，絕對不應該包含 "node_modules" 這個字串。
        self.assertNotIn("node_modules", final_content, "最終生成的目錄樹不應包含被忽略的 'node_modules' 目錄。")
        
        # 我們同時也斷言，應該包含 "src" 這個未被忽略的目錄，以確保更新確實發生了。
        self.assertIn("src", final_content, "最終生成的目錄樹應包含未被忽略的 'src' 目錄。")



    # 我們將在這裡插入我們的核心測試函式...

if __name__ == '__main__':
    unittest.main()
