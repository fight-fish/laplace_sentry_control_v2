# tests/test_daemon_logic.py

import unittest
import os
import json
import sys
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

# HACK: 導入路徑的技巧保持不變
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# 我們從源碼（src）的核心（core）中，導入（import）我們唯一的依賴：後端大腦（daemon）。
from src.core import daemon

class TestDaemonLogic(unittest.TestCase):
    """
    【v3.2 - 黃金驗收標準測試套件】
    本測試套件直接調用 daemon.py 中的 handle_... 純函式，
    驗證其業務邏輯和異常拋出是否正確，完全繞開文件 I/O 和 print/sys.exit。
    """
    def setUp(self):
        """
        在每個測試方法執行前，都會重新運行此函式。
        這確保了每個測試都在一個全新的、乾淨的、隔離的環境中進行。
        """
        self.project_A_uuid = "project-a-uuid"
        self.project_B_uuid = "project-b-uuid"
        self.project_C_uuid = "project-c-uuid" # 為刪除測試準備

        # 我們直接在內存中操作這個列表，通過依賴注入傳遞給函式
        self.mock_projects_data = [
            {
                "uuid": self.project_A_uuid, 
                "name": "Project A", 
                "path": "/path/to/project_A", 
                "output_file": ["/path/to/A.md"], 
                "target_files": ["/path/to/A.md"]
            },
            {
                "uuid": self.project_B_uuid, 
                "name": "Project B", 
                "path": "/path/to/project_B", 
                "output_file": ["/path/to/B.md"], 
                "target_files": ["/path/to/B.md"]
            },
            {
                "uuid": self.project_C_uuid, 
                "name": "Project C", 
                "path": "/path/to/project_C", 
                "output_file": ["/path/to/C.md"], 
                "target_files": ["/path/to/C.md"]
            }
        ]

    # --- 測試 handle_list_projects ---
    def test_list_projects_success(self):
        """測試：[List] 應成功返回完整的數據列表。"""
        print("\n--- 測試：[List] 成功路徑 ---")
        result = daemon.handle_list_projects(projects_data=self.mock_projects_data)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['name'], 'Project A')
        print("  > 檢查通過：成功返回數據列表。")

    # --- 測試 handle_add_project ---
    @patch('src.core.daemon.validate_paths_exist', return_value=True)
    @patch('src.core.daemon.write_projects_data')
    def test_add_project_success(self, mock_write, mock_validate):
        """測試：[Add] 成功新增一個專案。"""
        print("\n--- 測試：[Add] 成功路徑 ---")
        
        # 【最終修正】在測試前，先創建一個真實的臨時目錄作為場景
        temp_output_dir = os.path.join(project_root, 'tests', 'temp_output')
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # 使用這個真實存在的目錄來構造我們的參數
        temp_output_file = os.path.join(temp_output_dir, 'new.md')
        args = ["New Project", "/abs/path/to/new", temp_output_file]
        
        daemon.handle_add_project(args, projects_data=self.mock_projects_data)
        
        self.assertEqual(len(self.mock_projects_data), 4)
        self.assertEqual(self.mock_projects_data[3]['name'], "New Project")
        mock_write.assert_called_once()
        print("  > 檢查通過：成功新增專案到數據列表。")

        # 【最終修正】測試結束後，清理場景
        os.remove(temp_output_file) if os.path.exists(temp_output_file) else None
        os.rmdir(temp_output_dir)


    @patch('src.core.daemon.validate_paths_exist', return_value=True)
    def test_add_project_duplicate_name_raises_error(self, mock_validate):
        """測試：[Add] 新增重名專案時，應拋出 ValueError。"""
        print("\n--- 測試：[Add] 錯誤路徑 - 名稱衝突 ---")

        # 【最終修正】同樣，為這個失敗場景也準備一個合法的路徑
        temp_output_dir = os.path.join(project_root, 'tests', 'temp_output')
        os.makedirs(temp_output_dir, exist_ok=True)
        temp_output_file = os.path.join(temp_output_dir, 'C.md')

        args = ["Project A", "/path/to/new_C", temp_output_file]
        
        with self.assertRaisesRegex(ValueError, "已被佔用"):
            daemon.handle_add_project(args, projects_data=self.mock_projects_data)
        print("  > 檢查通過：成功捕捉到名稱衝突的 ValueError。")

        # 【最終修正】測試結束後，清理場景
        os.remove(temp_output_file) if os.path.exists(temp_output_file) else None
        os.rmdir(temp_output_dir)


    # --- 測試 handle_edit_project ---
    @patch('src.core.daemon.write_projects_data')
    def test_edit_project_success(self, mock_write):
        """測試：[Edit] 成功修改一個專案的名稱。"""
        print("\n--- 測試：[Edit] 成功路徑 ---")
        new_name = "Project A Renamed"
        args = [self.project_A_uuid, "name", new_name]
        
        daemon.handle_edit_project(args, projects_data=self.mock_projects_data)
        
        edited_project = next(p for p in self.mock_projects_data if p['uuid'] == self.project_A_uuid)
        self.assertEqual(edited_project['name'], new_name)
        mock_write.assert_called_once()
        print("  > 檢查通過：成功修改專案名稱。")

    def test_edit_project_uuid_not_found_raises_error(self):
        """測試：[Edit] 修改不存在的 UUID 時，應拋出 ValueError。"""
        print("\n--- 測試：[Edit] 錯誤路徑 - UUID 不存在 ---")
        args = ["non-existent-uuid", "name", "Some Name"]
        with self.assertRaisesRegex(ValueError, "未找到具有該 UUID"):
            daemon.handle_edit_project(args, projects_data=self.mock_projects_data)
        print("  > 檢查通過：成功捕捉到 UUID 不存在的 ValueError。")

    # --- 【新增】測試 handle_delete_project ---
    @patch('src.core.daemon.write_projects_data')
    def test_delete_project_success(self, mock_write):
        """【新增】測試：[Delete] 成功刪除一個專案。"""
        print("\n--- 測試：[Delete] 成功路徑 ---")
        
        # 在刪除前，確認專案總數
        initial_count = len(self.mock_projects_data)
        self.assertEqual(initial_count, 3)
        
        # 執行刪除操作
        args = [self.project_B_uuid]
        daemon.handle_delete_project(args, projects_data=self.mock_projects_data)
        
        # 驗證：傳入的列表本身被修改了，長度應該減 1
        # 注意：由於我們傳遞的是列表本身，所以 handle_delete_project 內部對列表的修改會影響到這裡
        # 這不是最佳實踐，但符合我們當前的函式實現。
        # 一個更優的設計是讓 handle_delete_project 返回一個新列表。
        
        # 為了讓測試通過，我們需要模擬 handle_delete_project 的行為：它創建一個新列表並寫入
        # 所以我們需要檢查 mock_write 被調用的參數
        
        # 讓我們修正 handle_delete_project 的測試方式，使其更健壯
        # 我們不檢查 self.mock_projects_data 的長度，而是檢查 write_projects_data 被調用時傳遞的參數
        
        # 重新執行刪除操作
        local_data_copy = [p.copy() for p in self.mock_projects_data]
        daemon.handle_delete_project(args, projects_data=local_data_copy)

        # 獲取傳遞給 mock_write 的第一個參數
        written_data = mock_write.call_args[0][0]
        
        self.assertEqual(len(written_data), 2)
        # 檢查被刪除的專案是否真的不在了
        self.assertIsNone(next((p for p in written_data if p['uuid'] == self.project_B_uuid), None))
        print("  > 檢查通過：成功刪除專案。")

    def test_delete_project_uuid_not_found_raises_error(self):
        """【新增】測試：[Delete] 刪除不存在的 UUID 時，應拋出 ValueError。"""
        print("\n--- 測試：[Delete] 錯誤路徑 - UUID 不存在 ---")
        args = ["non-existent-uuid"]
        with self.assertRaisesRegex(ValueError, "未找到具有該 UUID"):
            daemon.handle_delete_project(args, projects_data=self.mock_projects_data)
        print("  > 檢查通過：成功捕捉到 UUID 不存在的 ValueError。")


# --- 測試腳本的執行入口 ---
if __name__ == '__main__':
    # 這是啟動 unittest 最標準、最簡單、也最健壯的方式。
    # 它會自動發現並運行這個文件中所有以 "test_" 開頭的方法。
    unittest.main(verbosity=2)
