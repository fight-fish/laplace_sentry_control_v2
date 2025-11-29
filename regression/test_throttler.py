# regression/test_throttler.py (v3.0 - 嚴格驗收版)
import unittest
import os
import sys
import time
from unittest.mock import patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 使用 worker 裡面的 MockEvent (因為我們不再依賴 watchdog)
from src.core.sentry_worker import SmartThrottler, MockEvent

class TestSmartThrottler(unittest.TestCase):

    def test_single_file_overheat_triggers_file_muting(self):
        print("\n【SmartThrottler 測試】: 正在驗證『單檔過熱 (R1)』...")
        # 測試用：閾值 5
        throttler = SmartThrottler()
        target_file = "/path/to/main.py"
        
        for i in range(6):
            event = MockEvent(target_file, 'modified')
            throttler.should_process(event)
        
        self.assertIn(target_file, throttler.muted_paths)
        print("PASS")

    def test_burst_creation_triggers_directory_muting(self):
        print("\n【SmartThrottler 測試】: 正在驗證『爆量創建 (R3)』...")
        # 閾值 5
        throttler = SmartThrottler(burst_creation_threshold=5, burst_creation_period_seconds=1.0)
        target_dir = "/path/to/logs"
        
        for i in range(6):
            event = MockEvent(f"{target_dir}/log_{i}.txt", 'created')
            throttler.should_process(event)
            
        self.assertIn(target_dir, throttler.muted_paths)
        print("PASS")

    def test_abnormal_size_growth_triggers_file_muting(self):
        print("\n【SmartThrottler 測試】: 正在驗證『體積異常 (R4)』...")
        # 閾值 1MB
        throttler = SmartThrottler(size_growth_threshold_mb=1, size_growth_period_seconds=1.0)
        target_file = "/path/to/big.log"
        
        # 第一次：0MB
        evt1 = MockEvent(target_file, 'modified', file_size=0)
        throttler.should_process(evt1)
        self.assertNotIn(target_file, throttler.muted_paths)
        
        # 第二次：2MB (超過 1MB)
        evt2 = MockEvent(target_file, 'modified', file_size=2*1024*1024)
        throttler.should_process(evt2)
        
        self.assertIn(target_file, throttler.muted_paths)
        print("PASS")

if __name__ == '__main__':
    unittest.main()