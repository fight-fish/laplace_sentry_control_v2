import unittest
import os
import sys
import tempfile
import shutil
import json
from typing import List, Dict, Any # 導入類型提示，讓程式碼更清晰

# --- 測試環境準備 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)
from src.core import daemon

# --- 整合測試案例主體 ---
class TestIntegrationAtomicUpdate(unittest.TestCase):

    def setUp(self):
        """在 setUp 中，我們只準備數據，不再依賴環境變數。"""
        self.sandbox_dir = tempfile.mkdtemp()
        self.mock_project_path = os.path.join(self.sandbox_dir, "mock_project")
        os.makedirs(self.mock_project_path)
        with open(os.path.join(self.mock_project_path, "file.txt"), "w") as f:
            f.write("hello")

        self.mock_target_doc = os.path.join(self.sandbox_dir, "test.md")
        with open(self.mock_target_doc, "w") as f:
            f.write("Header\n<!-- AUTO_TREE_START -->\nOld tree\n<!-- AUTO_TREE_END -->\nFooter")
        
        self.project_uuid = "test-uuid-1234"
        # 我們將模擬的專案數據，作為一個屬性，存儲在測試實例中。
        self.mock_project_data: List[Dict[str, Any]] = [{
            "uuid": self.project_uuid,
            "name": "mock_project",
            "path": self.mock_project_path,
            "output_file": [self.mock_target_doc],
            "target_files": [self.mock_target_doc]
        }]
        
        # 【移除】我們不再需要設置或依賴任何環境變數。
        # os.environ['TEST_PROJECTS_FILE'] = self.mock_projects_file

    def tearDown(self):
        shutil.rmtree(self.sandbox_dir)
        # 【移除】也不再需要清理環境變數。
        # if 'TEST_PROJECTS_FILE' in os.environ:
        #     del os.environ['TEST_PROJECTS_FILE']

    def test_successful_atomic_update_flow(self):
        """
        測試目標：通過「依賴注入」，驗證 daemon.py 的整合能力。
        """
        try:
            # 【關鍵修改】
            # 我們在調用時，將準備好的 self.mock_project_data，
            # 作為 projects_data 參數，「注入」到函式中。
            daemon.handle_manual_update(
                [self.project_uuid], 
                projects_data=self.mock_project_data
            )
        except SystemExit as e:
            self.assertEqual(e.code, 0, f"Daemon 未能以退出碼 0 成功退出！ Stderr: {getattr(e, 'stderr', 'N/A')}")
        
        with open(self.mock_target_doc, 'r') as f:
            final_content = f.read()
        
        self.assertIn("Header", final_content)
        self.assertIn("Footer", final_content)
        self.assertIn("file.txt", final_content)
        self.assertNotIn("Old tree", final_content)

# --- 主執行區 ---
if __name__ == '__main__':
    os.chdir(PROJECT_ROOT)
    unittest.main()
