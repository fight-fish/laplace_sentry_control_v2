import unittest
import os
import sys
import shutil
import json
import time

# HACK: 確保能找到 src/core
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core import daemon

class TestSentryPersistence(unittest.TestCase):

    # 我們依然需要一個沙盒來放 projects.json，避免弄髒真的設定檔
    TEST_WORKSPACE = os.path.join(project_root, 'tests', 'test_workspace')
    TEST_DATA_DIR = os.path.join(TEST_WORKSPACE, 'data')
    TEST_PROJECTS_FILE = os.path.join(TEST_DATA_DIR, 'projects.json')

    def setUp(self):
        """
        測試前準備：
        1. 準備沙盒 data 目錄 (放 projects.json)
        2. 清理真實的 sentry 目錄 (確保測試環境乾淨)
        """
        # 1. 準備 projects.json 沙盒
        shutil.rmtree(self.TEST_WORKSPACE, ignore_errors=True)
        os.makedirs(self.TEST_DATA_DIR, exist_ok=True)
        with open(self.TEST_PROJECTS_FILE, 'w') as f:
            f.write('[]')
        os.environ['TEST_PROJECTS_FILE'] = self.TEST_PROJECTS_FILE

        # 2. 【核心策略調整】直接使用 daemon 的真實路徑，但要先清理乾淨
        #    注意：這會暫時清空你現在正在運行的所有哨兵記錄，請在測試機上運行。
        if os.path.exists(daemon.SENTRY_DIR):
            shutil.rmtree(daemon.SENTRY_DIR)
        os.makedirs(daemon.SENTRY_DIR, exist_ok=True)
        
        # 3. 確保 temp/projects 也存在
        os.makedirs(daemon.TEMP_PROJECTS_DIR, exist_ok=True)

    def tearDown(self):
        """測試後清理"""
        # 1. 清理沙盒
        shutil.rmtree(self.TEST_WORKSPACE, ignore_errors=True)
        if 'TEST_PROJECTS_FILE' in os.environ:
            del os.environ['TEST_PROJECTS_FILE']
            
        # 2. 再次清理真實 sentry 目錄，避免殘留
        if os.path.exists(daemon.SENTRY_DIR):
            shutil.rmtree(daemon.SENTRY_DIR)
        os.makedirs(daemon.SENTRY_DIR, exist_ok=True)

    def test_placeholder(self):
        self.assertTrue(True)

    def test_start_sentry_creates_pid_file_and_log(self):
        """驗證啟動哨兵後，真實的 PID 文件是否被創建"""
        fake_uuid = "uuid-start-test"
        # 使用 TEST_WORKSPACE 作為監控目標和輸出目標，避免權限問題
        fake_path = self.TEST_WORKSPACE
        fake_output = os.path.join(self.TEST_WORKSPACE, "out.md")
        
        projects = [{"uuid": fake_uuid, "name": "TestStart", "path": fake_path, "output_file": [fake_output]}]
        with open(self.TEST_PROJECTS_FILE, 'w') as f:
            json.dump(projects, f)

        daemon.main_dispatcher(['start_sentry', fake_uuid])
        time.sleep(1) # 給多一點時間啟動

        # 斷言：檢查 daemon.SENTRY_DIR 裡是否有檔案
        files = os.listdir(daemon.SENTRY_DIR)
        pid_files = [f for f in files if f.endswith('.sentry')]
        self.assertTrue(len(pid_files) > 0, f"在 {daemon.SENTRY_DIR} 中未發現 .sentry 文件！")
        
        # 讀取內容確認是我們的 UUID
        with open(os.path.join(daemon.SENTRY_DIR, pid_files[0]), 'r') as f:
            self.assertEqual(f.read().strip(), fake_uuid)

        # 清理：停止它
        daemon.main_dispatcher(['stop_sentry', fake_uuid])

    def test_stop_sentry_removes_pid_file(self):
        """驗證停止哨兵後，PID 文件被刪除"""
        fake_uuid = "uuid-stop-test"
        fake_path = self.TEST_WORKSPACE
        fake_output = os.path.join(self.TEST_WORKSPACE, "out_stop.md")
        
        projects = [{"uuid": fake_uuid, "name": "TestStop", "path": fake_path, "output_file": [fake_output]}]
        with open(self.TEST_PROJECTS_FILE, 'w') as f:
            json.dump(projects, f)

        # 啟動
        daemon.main_dispatcher(['start_sentry', fake_uuid])
        time.sleep(1)
        
        # 確認啟動成功
        self.assertTrue(len(os.listdir(daemon.SENTRY_DIR)) > 0)
        
        # 停止
        daemon.main_dispatcher(['stop_sentry', fake_uuid])
        time.sleep(0.5)
        
        # 斷言：目錄應該空了
        pid_files = [f for f in os.listdir(daemon.SENTRY_DIR) if f.endswith('.sentry')]
        self.assertEqual(len(pid_files), 0, "停止後 PID 文件依然存在！")

if __name__ == '__main__':
    unittest.main()