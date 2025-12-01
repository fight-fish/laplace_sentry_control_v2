import unittest
import os
import sys

# HACK: 確保能找到 src/core
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 從核心模組導入我們要測試的函式
from src.core.path import normalize_path

class TestPathNormalization(unittest.TestCase):

    # --- 1. 核心缺失功能測試 (應失敗 / RED LIGHT) ---
    def test_windows_drive_to_wsl_translation(self):
        """測試 Windows 磁碟機代號路徑是否能正確翻譯為 /mnt/d/... 格式"""
        # 模擬輸入：來自 Windows 檔案總管的標準路徑
        windows_path = "D:\\Obsidian\\Projects\\Test.md"
        
        # 預期輸出：WSL 格式的 /mnt/d/...
        expected_wsl_path = "/mnt/d/Obsidian/Projects/Test.md"
        
        # 設置環境變數模擬在非 Windows 環境下運行 (os.name != 'nt')
        # HACK: 我們需要一個方法來暫時模擬 os.name != 'nt' 的情況
        # 由於 unittest.mock 依賴性較大，我們暫時假設測試在 WSL 中運行。
        # NOTE: 實際的 RED LIGHT 將在運行時由 os.name 判斷觸發。
        
        # 這是目前錯誤的行為，目的是讓測試失敗 (RED)
        result = normalize_path(windows_path)
        
        # 由於當前 path.py 缺乏對 D:/ 格式的完整處理，這個測試在 WSL 中會失敗
        self.assertEqual(result, expected_wsl_path, "Windows 磁碟機代號轉換為 WSL /mnt/d/... 失敗。")


    # --- 2. 迴歸測試 (應通過 / GREEN LIGHT) ---
    def test_linux_and_wsl_path_regressions(self):
        """測試修正 Windows 路徑後，不破壞其他正常路徑"""
        
        # 測試 2.1: 標準 Linux 絕對路徑
        linux_path = "/home/user/project/file.py"
        self.assertEqual(normalize_path(linux_path), linux_path, "Linux 路徑不應被修改。")
        
        # 測試 2.2: 已經轉換過的 WSL UNC 路徑 (應保持原樣或僅刪除主機名)
        wsl_unc = "//wsl.localhost/Ubuntu/home/user/file.py"
        # 根據 path.py 邏輯，在非 Windows 環境下，應被轉為 /home/user/file.py
        expected = "/home/user/file.py" 
        
        # 由於我們沒有 Mock os.name，這個測試是為了驗證現有邏輯的穩定性
        self.assertEqual(normalize_path(wsl_unc), expected, "WSL UNC 轉換迴歸測試失敗。")
        
        # 測試 2.3: 處理多餘引號
        quoted_path = "'/home/user/project'"
        self.assertEqual(normalize_path(quoted_path), "/home/user/project", "多餘引號剝離迴歸測試失敗。")


if __name__ == '__main__':
    unittest.main()