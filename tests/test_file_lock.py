# tests/test_file_lock.py

import unittest
import os
import sys
import json
import time
from multiprocessing import Process, Manager

# --- 核心：我們現在直接導入我們要測試的「I/O 網關」 ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from src.core.io_gateway import safe_read_modify_write

# --- 測試用的「假工人」函式，現在直接使用 I/O 網關 ---
def worker_process(file_path, process_id, results_dict):
    """
    這個工人模擬一個需要對文件進行「讀-改-寫」的業務場景。
    它將完全通過 io_gateway 來執行此操作。
    """
    for i in range(5):
        try:
            # 我們定義一個「修改」的回調函式
            def append_entry_callback(current_data):
                # 模擬計算耗時
                time.sleep(0.01) 
                # 執行修改邏輯
                new_entry = {'process_id': process_id, 'write_no': i}
                current_data.append(new_entry)
                return current_data

            # 【核心測試點】調用 I/O 網關，執行完整的、原子的「讀-改-寫」事務
            safe_read_modify_write(file_path, append_entry_callback, serializer='json')

        except Exception as e:
            results_dict['error'] = str(e)
            return
            
    results_dict[process_id] = 'success'


class TestFileLock(unittest.TestCase):

    def setUp(self):
        self.test_file = os.path.join(project_root, 'tests', 'temp_lock_test.json')
        # 為了防止意外，我們也為測試文件本身創建伴生鎖，並在測試前清理
        self.lock_file = self.test_file + ".lock"
        
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
            
        # 確保初始文件是有效的 JSON 數組
        with open(self.test_file, 'w') as f:
            f.write("[]")

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    def test_concurrent_write_with_gateway(self):
        """
        【終局驗收】：驗證在「I/O 網關」的保護下，並發寫入能保證數據的絕對完整性。
        """
        print("\n--- 測試開始：驗證「I/O 網關」的並發保護能力 ---")
        
        with Manager() as manager:
            results = manager.dict()
            p1 = Process(target=worker_process, args=(self.test_file, 'p1', results))
            p2 = Process(target=worker_process, args=(self.test_file, 'p2', results))
            
            p1.start()
            p2.start()
            p1.join()
            p2.join()

            if 'error' in results:
                self.fail(f"測試過程中發生意外錯誤: {results['error']}")

        with open(self.test_file, 'r') as f:
            final_data = json.load(f)
        
        final_length = len(final_data)
        print(f"兩個進程各寫入 5 次，預期總長度為 10。")
        print(f"在「I/O 網關」保護下，最終文件的實際長度為: {final_length}")

        # 【核心斷言】我們現在期望，最終的長度必須等於 10！
        self.assertEqual(final_length, 10, "【警報】：I/O 網關鎖無效！數據依然發生了丟失！")

# --- 測試執行入口 ---
if __name__ == '__main__':
    unittest.main()
