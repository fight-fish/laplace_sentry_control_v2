# tests/test_timeout.py
import unittest
import sys
import os
import time
import pytest
import subprocess # 導入 subprocess

# --- 核心：導入我們要測試的目標函式 ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from src.core.daemon import _run_single_update_workflow
@pytest.mark.skip(reason="Legacy timeout design (old subprocess workflow), will be redesigned after daemon refactor.")
class TestTimeoutMechanism(unittest.TestCase):


# 位於 tests/test_timeout.py

    def test_workflow_should_timeout_gracefully(self):
        """
        【驗證測試】：驗證 _run_single_update_workflow 在子進程超時時能優雅失敗。
        """
        print("\n--- 測試開始：驗證超時保護機制 ---")
        print("預期行為：本測試將在 10 秒左右被強制中止，並報告超時。")

        # --- 【關鍵修正 v2】創建一個真實的臨時目錄來繞過第一道防線 ---
        temp_project_dir = os.path.join(project_root, 'tests', 'temp_test_dir_for_timeout')
        os.makedirs(temp_project_dir, exist_ok=True)

        # --- 測試設置：用「假專家」替換掉「真專家」 ---
        original_path_script = os.path.join(project_root, 'src', 'core', 'path.py')
        fake_expert_path = os.path.join(project_root, 'tests', 'fake_expert_sleeps.py')
        
        os.rename(original_path_script, original_path_script + ".bak")
        os.symlink(fake_expert_path, original_path_script)

        start_time = time.time()
        
        # 【核心觀測點】直接調用我們修改過的、真正的 daemon 函式
        # 【關鍵修正 v2】傳入真實存在的臨時目錄
        exit_code, result_message = _run_single_update_workflow(
            temp_project_dir, 
            "/fake/target.md" # target_doc 的檢查在後面，所以這裡用假的沒關係
        )
        
        end_time = time.time()
        duration = end_time - start_time

        # --- 清理現場：無論如何都要恢復原始文件和刪除臨時目錄 ---
        os.remove(original_path_script)
        os.rename(original_path_script + ".bak", original_path_script)
        os.rmdir(temp_project_dir) # 刪除我們創建的臨時目錄

        print(f"測試執行完畢。耗時: {duration:.2f} 秒。")
        print(f"函式返回碼: {exit_code}")
        print(f"函式返回信息:\n{result_message.strip()}")

        # 【核心斷言】(保持不變)
        self.assertLess(duration, 15.0)
        self.assertEqual(exit_code, 3)
        self.assertIn("超時", result_message)


# --- 測試執行入口 ---
if __name__ == '__main__':
    unittest.main()
