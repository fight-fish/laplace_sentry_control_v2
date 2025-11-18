# regression/test_throttler.py (v2.0 - 重生版考卷)

import unittest
import os
import sys
import time
from unittest.mock import patch, Mock

# HACK: 確保能找到 src/core 下的源碼
project_root = os.getcwd()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 我們從 watchdog 導入真實的事件類型，以便進行更精準的測試
from watchdog.events import FileCreatedEvent, FileModifiedEvent

# 【注意】我們現在導入的是一個「尚不存在」的 SmartThrottler
# 這正是 TDD 的精髓：先寫測試，再寫實現。
from src.core.sentry_worker import SmartThrottler, SENTRY_INTERNAL_IGNORE

class TestSmartThrottler(unittest.TestCase):

    def test_single_file_overheat_triggers_file_muting(self):
        """
        【TDD 測試 R1：單檔過熱】
        驗證同一個文件在短時間內被頻繁修改，會導致該「文件」被靜默。
        """
        print("\n【SmartThrottler 測試】: 正在驗證『單檔過熱靜默 (R1)』...")
        
        throttler = SmartThrottler()
        
        target_file = "/path/to/project/src/main.py"
        
        # 我們模擬在 5 秒內，連續修改同一個文件 6 次
        # 使用 patch 模擬文件存在，避免 os.stat() 報錯
        with patch('os.stat') as mock_stat:
            mock_stat.return_value.st_size = 1024  # 假設文件大小為 1KB
            for i in range(6):
                event = FileModifiedEvent(src_path=target_file)
                throttler.should_process(event)
                time.sleep(0.1)
        
        # 【最終斷言】
        self.assertIn(
            target_file,
            throttler.muted_paths,
            "單檔過熱後，該文件未能被添加到 muted_paths 黑名單中。"
        )
        print("【SmartThrottler 測試】: 『單檔過熱靜默』功能驗證通過！")



    def test_burst_creation_triggers_directory_muting(self):
        """
        【TDD 測試 I：爆量創建 (R3)】
        驗證在一個目錄下短時間內創建大量文件，會導致該「目錄」被靜默。
        """
        print("\n【SmartThrottler 測試】: 正在驗證『爆量創建靜默 (R3)』...")
        
        # 我們創建一個對「爆量創建」極其敏感的 throttler
        # 規則：在 0.2 秒內，創建超過 5 個文件，就算爆量。
        throttler = SmartThrottler(burst_creation_threshold=5, burst_creation_period_seconds=0.2)

        target_dir = "/path/to/project/node_modules/some_lib"

        # 我們模擬在 0.2 秒內，連續創建 6 個位於同一目錄下的文件
        for i in range(6):
            event = FileCreatedEvent(src_path=f"{target_dir}/file_{i}.js")
            # 我們直接調用 should_process，因為這是我們要測試的核心邏輯
            throttler.should_process(event)
            time.sleep(0.01) # 模擬極短的時間間隔

        # 【最終斷言】
        # 我們斷言，那個作祟的「目錄」，現在必須出現在 muted_paths 黑名單中。
        self.assertIn(
            target_dir,
            throttler.muted_paths,
            "發生爆量創建後，其父目錄未能被添加到 muted_paths 黑名單中。"
        )
        print("【SmartThrottler 測試】: 『爆量創建靜默』功能驗證通過！")


    def test_abnormal_size_growth_triggers_file_muting(self):
        """
        【TDD 測試 II：體積異常 (R4)】
        驗證一個文件的大小在短時間內劇增，會導致該「文件」被靜默。
        """
        print("\n【SmartThrottler 測試】: 正在驗證『體積異常靜默 (R4)』...")

        # 我們創建一個對體積增長極其敏感的 throttler
        # 規則：在 0.2 秒內，體積增長超過 1MB，就算異常。
        throttler = SmartThrottler(size_growth_threshold_mb=1, size_growth_period_seconds=0.2)

        target_file = "/path/to/project/logs/app.log"

        # 我們使用 patch 來模擬 `os.stat().st_size` 的返回值
        # 這是進行 I/O 相關單元測試的黃金標準技巧
        
        # 第一次事件：文件大小為 0
        with patch('os.stat') as mock_stat:
            # 讓 os.stat() 返回一個 st_size 為 0 的對象
            mock_stat.return_value.st_size = 0
            event1 = FileModifiedEvent(src_path=target_file)
            throttler.should_process(event1)

        # 我們斷言，此時文件還不應該被靜默
        self.assertNotIn(target_file, throttler.muted_paths, "第一次修改後，文件不應該被靜默。")

        # 短暫休眠，確保在時間窗口內
        time.sleep(0.01)

        # 第二次事件：文件大小劇增到 2MB
        with patch('os.stat') as mock_stat:
            # 讓 os.stat() 返回一個 st_size 為 2MB 的對象
            mock_stat.return_value.st_size = 2 * 1024 * 1024
            event2 = FileModifiedEvent(src_path=target_file)
            throttler.should_process(event2)

        # 【最終斷言】
        # 我們斷言，在經歷了體積劇增後，這個文件現在必須被靜默。
        self.assertIn(
            target_file,
            throttler.muted_paths,
            "文件體積發生異常增長後，未能被添加到 muted_paths 黑名單中。"
        )
        print("【SmartThrottler 測試】: 『體積異常靜默』功能驗證通過！")

    def test_basic_throttling_works(self):
        """
        【安全網測試】
        驗證正常的、低頻的文件修改事件,不會觸發靜默機制。
        """
        print("\n【SmartThrottler 測試】: 正在驗證『正常事件不被誤判』...")
        
        throttler = SmartThrottler()
        
        target_file = "/path/to/project/src/utils.py"
        
        # 我們模擬一個正常的使用場景:
        # 用戶在 10 秒內,只修改了同一個文件 3 次（低於 5 次的閾值）
        with patch('os.stat') as mock_stat:
            mock_stat.return_value.st_size = 2048  # 假設文件大小為 2KB
            
            for i in range(3):
                event = FileModifiedEvent(src_path=target_file)
                result = throttler.should_process(event)
                # 每次都應該返回 True,表示允許處理
                self.assertTrue(
                    result,
                    f"第 {i+1} 次正常修改事件被錯誤地拒絕了。"
                )
                time.sleep(2)  # 每次修改間隔 2 秒,模擬正常的編輯節奏
        
        # 【最終斷言】
        # 我們斷言,在正常使用情況下,文件不應該被靜默
        self.assertNotIn(
            target_file,
            throttler.muted_paths,
            "正常的低頻修改事件,錯誤地觸發了靜默機制。"
        )
        print("【SmartThrottler 測試】: 『正常事件不被誤判』功能驗證通過!")



# 這是一個 Python 的標準寫法。
if __name__ == '__main__':
    unittest.main()
