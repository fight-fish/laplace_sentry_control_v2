import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import tempfile
import shutil
from io import StringIO # 我們將 StringIO 的導入放在頂部，保持風格統一。

# --- 測試環境準備 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

# 我們使用「絕對導入」，從 src.core 這個明確的路徑導入 path 模組。
from src.core import path

# --- 測試案例主體 ---
# ... 其他程式碼保持不變 ...

class TestAtomicWriteV2(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.target_file = os.path.join(self.test_dir, "target.txt")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    # 【關鍵修改】
    # 我們在 patch os.replace 時，增加一個 wraps=os.replace 參數。
    # 這告訴 mock：「在監視 os.replace 的同時，也請執行它本來的功能！」
    @patch('os.fsync')
    @patch('os.replace', wraps=os.replace) 
    def test_fsync_is_called(self, mock_replace, mock_fsync):
        """
        【v2 核心測試】
        測試目標：驗證在執行原子寫入時，os.fsync 是否被正確調用。
        """
        # ... 後續的測試邏輯與您的版本完全一樣，無需改動 ...
        content = "ensure this is synced"
        
        test_args = ["path.py", "atomic_write", self.target_file]
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdin', new=StringIO(content)):
                try:
                    path.main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0, "path.main() 應以退出碼 0 成功退出。")

        # --- 【最終驗收】 ---
        mock_fsync.assert_called_once()
        mock_replace.assert_called_once()
        
        with open(self.target_file, 'r') as f:
            self.assertEqual(f.read(), content)

        print("\n✅ [PASS] 驗證成功：os.fsync 在原子寫入流程中被正確調用，且文件內容正確。")

# ... 其他程式碼保持不變 ...

if __name__ == '__main__':
    unittest.main()
