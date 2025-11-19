# 我們需要 導入（import）所有用於測試的工具。
import unittest
import os
import sys
import shutil
import json
from typing import List, Dict, Any

# HACK: 讓測試可以找到專案裡的 src/ 目錄
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 現在，我們可以安全地從 src.core 中，導入我們的「指揮官」模塊了。
from src.core import daemon

# 我們用「class」關鍵字，來定義一個我們自己的「回歸測試套件」。
# 它的名字，清晰地表明了它的使命：守護 v8 版本的穩定性。
class TestRegressionSuiteV8(unittest.TestCase):

    # --- 【v2 - 安全沙盒版】 ---
    # 我們定義一個類屬性，用來存放我們「一次性沙盒」的路徑。
    TEST_WORKSPACE = os.path.join(PROJECT_ROOT, 'tests', 'regression', 'test_workspace')
    TEST_DATA_DIR = os.path.join(TEST_WORKSPACE, 'data')
    TEST_TEMP_DIR = os.path.join(TEST_WORKSPACE, 'temp')
    TEST_PROJECTS_FILE = os.path.join(TEST_DATA_DIR, 'projects.json')

    # 我們用「def setUp」來定義一個特殊的「測試前準備」方法。
    def setUp(self):
        """在每個測試開始前，搭建一個乾淨、隔離的沙盒環境。"""
        shutil.rmtree(self.TEST_WORKSPACE, ignore_errors=True)
        os.makedirs(self.TEST_DATA_DIR, exist_ok=True)
        os.makedirs(self.TEST_TEMP_DIR, exist_ok=True)
        
        with open(self.TEST_PROJECTS_FILE, 'w') as f:
            f.write('[]')
            
        os.environ['TEST_PROJECTS_FILE'] = self.TEST_PROJECTS_FILE
        # 【核心改造】我們在這裡，激活「測試模式」。
        os.environ['LAPLACE_TEST_MODE'] = '1' 
        daemon.running_sentries.clear()

    # 我們用「def tearDown」來定義一個特殊的「測試後清理」方法。
    def tearDown(self):
        """在每個測試結束後，徹底銷毀沙盒環境。"""
        shutil.rmtree(self.TEST_WORKSPACE, ignore_errors=True)
        if 'TEST_PROJECTS_FILE' in os.environ:
            del os.environ['TEST_PROJECTS_FILE']
                # 【核心改造】我們在這裡，取消「測試模式」。
        if 'LAPLACE_TEST_MODE' in os.environ:
            del os.environ['LAPLACE_TEST_MODE']

        # --- 輔助斷言函式 ---
    # 我們定義一個輔助函式，專門用來檢查「預期的失敗」。
    def assertFailsWith(self, command_and_args: List[str], expected_error_message: str, **kwargs):
        """
        【v2.0 - 專業版】
        一個輔助斷言，它在一次呼叫中，同時驗證：
        1. 指令確實拋出了我們預期的異常類型。
        2. 拋出的異常中，包含我們預期的錯誤信息文本。
        """
        # 我們用一個「上下文管理器（with self.assertRaises(...)）」來精準地捕獲預期的異常。
        # 我們將捕獲到的異常對象，存儲在變數 `cm` (Context Manager) 中。
        with self.assertRaises((ValueError, IOError, RuntimeError), msg=f"指令 {command_and_args} 未能如預期般拋出異常") as cm:
            # 我們只在這裡，運行一次指令。
            daemon.main_dispatcher(command_and_args, **kwargs)
        
        # 在 with 塊結束後，我們就可以從 cm.exception 中，獲取那個被捕獲到的異常對象。
        # 然後，我們斷言，預期的錯誤信息，確實出現在了這個異常對象的文本內容中。
        self.assertIn(expected_error_message, str(cm.exception), "後端返回的錯誤信息與預期不符。")

    # --- 核心測試：全生命週期 ---
    def test_project_full_lifecycle(self):
        """
        【黃金標準測試】
        在一個測試用例中，完整地、按順序地驗證專案的「增、改、查、刪」全生命週期。
        """
        print("\n【回歸測試】: 正在執行『專案全生命週期』測試...")

        # --- 階段 1: 新增一個專案 ---
        print("  -> 階段 1: 測試『新增專案』...")
        project_name = "我的第一個專案"
        # 我們在沙盒的 temp 目錄下，創建一個假的專案路徑，確保它真實存在。
        project_path = os.path.join(self.TEST_TEMP_DIR, "my_first_project")
        os.makedirs(project_path)
        output_file = os.path.join(self.TEST_TEMP_DIR, "output.md")
        
        # 執行新增指令
        add_result = daemon.main_dispatcher(
            ['add_project', project_name, project_path, output_file],
            projects_file_path=self.TEST_PROJECTS_FILE
)
        self.assertEqual(add_result, 0, "新增專案時，後端未能返回成功的退出碼 0。")

        # --- 階段 2: 驗證新增結果 ---
        print("  -> 階段 2: 驗證『新增結果』...")
        projects = daemon.handle_list_projects(projects_file_path=self.TEST_PROJECTS_FILE)
        self.assertEqual(len(projects), 1, "新增後，專案列表的長度不為 1。")
        created_project = projects[0]
        self.assertEqual(created_project['name'], project_name, "新增後，專案的名稱不正確。")
        # 我們需要獲取新增專案的 UUID，以便後續操作。
        project_uuid = created_project['uuid']


        # --- 階段 3: 驗證所有「新增失敗」的場景 ---
        print("  -> 階段 3: 驗證所有『新增失敗』場景...")
        # 3.1 測試重名
        self.assertFailsWith(
            ['add_project', project_name, project_path, output_file],
            f"專案別名 '{project_name}' 已被佔用。",
            projects_file_path=self.TEST_PROJECTS_FILE
        )
        # 3.2 測試重路徑
        self.assertFailsWith(
            ['add_project', "不同的名字", project_path, output_file],
            f"專案路徑 '{project_path}' 已被其他專案監控。",
            kwargs={'projects_file_path': self.TEST_PROJECTS_FILE}
        )

        # --- 【v9.2 測試修正】 ---
        # 為了測試「目標文件重複」，我們必須先創造一個不與現有專案衝突的「新專案路徑」。
        # 1. 我們在沙盒中，創建一個全新的、合法的專案目錄。
        another_valid_path = os.path.join(self.TEST_TEMP_DIR, "another_project")
        os.makedirs(another_valid_path)

        # 2. 然後，在測試指令中，我們使用這個【真實存在】的路徑。
        #    這樣，路徑檢查關卡就會放行，測試才能繼續進行到「目標文件重複」的檢查。
        self.assertFailsWith(
            ['add_project', "不同的名字", another_valid_path, output_file], 
            f"目標文件 '{output_file}' 已被專案 '{project_name}' 使用。",
            kwargs={'projects_file_path': self.TEST_PROJECTS_FILE}
        )


        # --- 階段 4: 修改專案名稱 ---
        print("  -> 階段 4: 測試『修改專案』...")
        new_project_name = "改名後的專案"
        edit_result = daemon.main_dispatcher(
    ['edit_project', project_uuid, 'name', new_project_name],
    projects_file_path=self.TEST_PROJECTS_FILE
)

        self.assertEqual(edit_result, 0, "修改專案名稱時，後端未能返回成功的退出碼 0。")
        
        # --- 階段 5: 驗證修改結果 ---
        print("  -> 階段 5: 驗證『修改結果』...")
        projects_after_edit = daemon.handle_list_projects(projects_file_path=self.TEST_PROJECTS_FILE)
        edited_project = projects_after_edit[0]
        self.assertEqual(edited_project['name'], new_project_name, "修改後，專案的名稱未被更新。")

        # --- 階段 6: 刪除專案 ---
        print("  -> 階段 6: 測試『刪除專案』...")
        delete_result = daemon.main_dispatcher(
    ['delete_project', project_uuid],
    projects_file_path=self.TEST_PROJECTS_FILE
)

        self.assertEqual(delete_result, 0, "刪除專案時，後端未能返回成功的退出碼 0。")

        # --- 階段 7: 驗證刪除結果 ---
        print("  -> 階段 7: 驗證『刪除結果』...")
        projects_after_delete = daemon.handle_list_projects(projects_file_path=self.TEST_PROJECTS_FILE)

        self.assertEqual(len(projects_after_delete), 0, "刪除後，專案列表應為空。")
        
        print("【回歸測試】: 『專案全生命週期』測試通過！")


# 這是一個 Python 的標準寫法。
if __name__ == '__main__':
    unittest.main()

