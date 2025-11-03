# tests/test_edit_delete.py

# 我們需要的標準工具
import unittest
import subprocess
import os
import json
import shutil
import sys

# 這是 Python 的慣例，確保測試腳本能找到位於 src/ 目錄下的模塊
# 我們將專案的根目錄（即 tests/ 的上一級目錄）添加到 Python 的搜索路徑中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# 【重要】現在我們可以安全地從 src.core 導入 path 模塊中的工具了
# 這讓我們可以在測試中，也使用和 daemon.py 完全一樣的路徑淨化邏輯
from src.core.path import normalize_path

class TestEditDeleteProject(unittest.TestCase):
    """
    針對 daemon.py 中 edit_project 和 delete_project 指令的契約測試套件。
    """
    
    # 測試環境準備 (Setup)
    def setUp(self):
        """在每個測試函式執行前，都會運行的準備工作。"""
        # 1. 定義測試所需的各種路徑
        self.daemon_path = os.path.join(project_root, 'src', 'core', 'daemon.py')
        self.test_data_dir = os.path.join(project_root, 'tests', 'temp_data')
        self.mock_projects_file = os.path.join(self.test_data_dir, 'projects.json')
        
        # 2. 創建一個乾淨的臨時數據目錄
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # 3. 定義我們的「初始世界狀態」
        self.proj_a_uuid = "a0000001-a001-a001-a001-a00000000001"
        self.proj_b_uuid = "b0000002-b002-b002-b002-b00000000002"
        
        # 為了測試路徑存在性，我們需要創建一個真實的目錄
        self.real_path_for_edit = os.path.join(self.test_data_dir, 'a_real_project_dir')
        os.makedirs(self.real_path_for_edit, exist_ok=True)

        self.initial_data = [
            {
                "uuid": self.proj_a_uuid,
                "name": "Project A",
                "path": normalize_path("C:\\Users\\Pal\\Project_A"),
                "target_files": [normalize_path("D:\\Obsidian\\Note_A.md")]
            },
            {
                "uuid": self.proj_b_uuid,
                "name": "Project B",
                "path": normalize_path("C:\\Users\\Pal\\Project_B"),
                "target_files": [normalize_path("D:\\Obsidian\\Note_B.md")]
            }
        ]
        
        # 4. 將初始狀態寫入 mock_projects.json 文件
        with open(self.mock_projects_file, 'w', encoding='utf-8') as f:
            json.dump(self.initial_data, f, indent=2)

    # 測試環境清理 (Teardown)
    def tearDown(self):
        """在每個測試函式執行後，都會運行的清理工作。"""
        # 刪除臨時創建的數據目錄及其所有內容
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    def run_daemon_command(self, command_parts):
        """一個輔助函式，用於執行 daemon.py 命令並返回結果。"""
        # 【關鍵】我們必須告訴 daemon.py 去使用我們的 mock_projects.json 文件
        # 我們通過一個特殊的環境變數來傳遞這個信息
        env = os.environ.copy()
        env['TEST_PROJECTS_FILE'] = self.mock_projects_file
        
        # 組合完整的命令
        full_command = [sys.executable, self.daemon_path] + command_parts
        
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=env
        )
        return result

    # --- 測試 edit_project ---

    def test_edit_name_success(self):
        """1.1.1 測試用例：成功修改專案名稱"""
        result = self.run_daemon_command(['edit_project', self.proj_a_uuid, 'name', 'Project Alpha'])
        
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "OK")
        
        with open(self.mock_projects_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data[0]['name'], 'Project Alpha') # 驗證名稱已修改
        self.assertEqual(data[1]['name'], 'Project B')     # 驗證其他專案未受影響

    def test_edit_path_success(self):
        """1.1.2 測試用例：成功修改專案路徑"""
        new_path = self.real_path_for_edit
        result = self.run_daemon_command(['edit_project', self.proj_a_uuid, 'path', new_path])
        
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "OK")
        
        with open(self.mock_projects_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(normalize_path(data[0]['path']), normalize_path(new_path))

    def test_edit_uuid_not_found(self):
        """1.2.1 測試用例：嘗試編輯一個不存在的 UUID"""
        fake_uuid = "f0000000-f000-f000-f000-f00000000000"
        result = self.run_daemon_command(['edit_project', fake_uuid, 'name', 'New Name'])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("【編輯失敗】：未找到具有該 UUID 的專案。", result.stderr)

    def test_edit_invalid_field(self):
        """1.2.2 測試用例：嘗試修改一個不允許的欄位（如 uuid）"""
        result = self.run_daemon_command(['edit_project', self.proj_a_uuid, 'uuid', 'new_uuid'])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("【編輯失敗】：無效的欄位名稱。", result.stderr)

    def test_edit_name_conflict(self):
        """1.2.3 測試用例：嘗試將名稱修改為一個已存在的名稱"""
        result = self.run_daemon_command(['edit_project', self.proj_a_uuid, 'name', 'Project B'])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("【編輯失敗】：新的專案別名已被佔用。", result.stderr)

    def test_edit_path_conflict(self):
        """1.2.4 測試用例：嘗試將路徑修改為一個已存在的路徑"""
        path_of_b = self.initial_data[1]['path']
        result = self.run_daemon_command(['edit_project', self.proj_a_uuid, 'path', path_of_b])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("【編輯失敗】：新的專案路徑已被其他專案監控。", result.stderr)

    def test_edit_path_not_exist(self):
        """1.2.5 測試用例：嘗試將路徑修改為一個不存在的路徑"""
        fake_path = "C:\\path\\that\\does\\not\\exist"
        result = self.run_daemon_command(['edit_project', self.proj_a_uuid, 'path', fake_path])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("【編輯失敗】：新的路徑不存在或無效。", result.stderr)

    def test_edit_wrong_arg_count(self):
        """1.2.6 測試用例：使用錯誤的參數數量調用 edit_project"""
        result = self.run_daemon_command(['edit_project', self.proj_a_uuid, 'name'])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("【編輯失敗】：參數數量不正確", result.stderr)

    # --- 測試 delete_project ---

    def test_delete_success(self):
        """2.1.1 測試用例：成功刪除一個專案"""
        result = self.run_daemon_command(['delete_project', self.proj_a_uuid])
        
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "OK")
        
        with open(self.mock_projects_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.assertEqual(len(data), 1) # 驗證只剩下一個專案
        self.assertEqual(data[0]['uuid'], self.proj_b_uuid) # 驗證剩下的是 Project B

    def test_delete_uuid_not_found(self):
        """2.2.1 測試用例：嘗試刪除一個不存在的 UUID"""
        fake_uuid = "f0000000-f000-f000-f000-f00000000000"
        result = self.run_daemon_command(['delete_project', fake_uuid])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("【刪除失敗】：未找到具有該 UUID 的專案。", result.stderr)

    def test_delete_wrong_arg_count(self):
        """2.2.2 測試用例：使用錯誤的參數數量調用 delete_project"""
        result = self.run_daemon_command(['delete_project'])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("【刪除失敗】：參數數量不正確", result.stderr)

# 這是 unittest 框架的標準入口點
if __name__ == '__main__':
    unittest.main()
