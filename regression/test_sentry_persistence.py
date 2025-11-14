# 我們需要 導入（import）所有用於測試的工具。
import unittest
import os
import sys
import shutil
import json

# HACK: 為了能讓測試腳本，找到位於 src/core 目錄下的源碼，
# 我們需要手動將專案的根目錄，添加到 Python 的「搜索路徑」中。
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# 現在，我們可以安全地從 src.core 中，導入我們的「指揮官」模塊了。
from src.core import daemon

# 我們用「class」關鍵字，來定義一個我們自己的「測試案例集」。
# 它繼承自 unittest.TestCase，這意味著它擁有執行測試的能力。
class TestSentryPersistence(unittest.TestCase):

    # --- 【v2 - 安全沙盒版】 ---
    # 我們定義一個類屬性，用來存放我們「一次性沙盒」的路徑。
    TEST_WORKSPACE = os.path.join(project_root, 'tests', 'test_workspace')
    # 我們定義沙盒中，data 和 temp 目錄的具體路徑。
    TEST_DATA_DIR = os.path.join(TEST_WORKSPACE, 'data')
    TEST_TEMP_DIR = os.path.join(TEST_WORKSPACE, 'temp')
    # 我們定義沙盒中，那個假的 projects.json 文件的路徑。
    TEST_PROJECTS_FILE = os.path.join(TEST_DATA_DIR, 'projects.json')

    # 我們用「def setUp」來定義一個特殊的「測試前準備」方法。
    # 在這個類中的「每一個」測試方法（以 test_ 開頭的）運行之前，
    # unittest 框架都會自動地、優先地調用一次 setUp。
    def setUp(self):
        """在每個測試開始前，搭建一個乾淨、隔離的沙盒環境。"""
        
        # 1. 我們先用 shutil.rmtree 粗暴地刪除可能殘留的舊沙盒，確保絕對乾淨。
        #    ignore_errors=True 確保了即使沙盒不存在，也不會報錯。
        shutil.rmtree(self.TEST_WORKSPACE, ignore_errors=True)
        
        # 2. 我們用 os.makedirs 創建沙盒的基礎目錄結構。
        os.makedirs(self.TEST_DATA_DIR, exist_ok=True)
        os.makedirs(self.TEST_TEMP_DIR, exist_ok=True)
        
        # 3. 我們向那個假的 projects.json 文件中，寫入一個空的 JSON 列表 `[]`。
        with open(self.TEST_PROJECTS_FILE, 'w') as f:
            f.write('[]')
            
        # 4. 【核心安全機制】我們設置環境變數，將 daemon 的 I/O 操作重定向到我們的沙盒。
        os.environ['TEST_PROJECTS_FILE'] = self.TEST_PROJECTS_FILE
        
        # 5. 我們清空 daemon 內存中可能殘留的、來自上一個測試的哨兵記錄。
        #    這確保了每個測試的「戶口名簿」都是從零開始的。
        daemon.running_sentries.clear()

    # 我們用「def tearDown」來定義一個特殊的「測試後清理」方法。
    # 在這個類中的「每一個」測試方法運行結束之後（無論成功還是失敗），
    # unittest 框架都會自動地調用一次 tearDown。
    def tearDown(self):
        """在每個測試結束後，徹底銷毀沙盒環境。"""
        
        # 1. 我們再次粗暴地刪除整個沙盒文件夾。
        shutil.rmtree(self.TEST_WORKSPACE, ignore_errors=True)
        
        # 2. 【核心安全機制】我們刪除之前設置的環境變數，防止它「洩漏」到其他測試中。
        if 'TEST_PROJECTS_FILE' in os.environ:
            del os.environ['TEST_PROJECTS_FILE']

    # --- 我們的第一個「佔位」測試 ---
    # 所有的測試方法，都必須以「test_」作為開頭。
    def test_placeholder(self):
        """一個什麼都不做的佔位測試，用來驗證我們的腳手架是否能正常運行。"""
        # 我們用 self.assertTrue(True) 這個斷言，來表示這個測試無條件通過。
        self.assertTrue(True)
        print("\n【測試日誌】: `test_placeholder` 執行完畢。腳手架工作正常！")

    # 我們用「def」來定義一個新的測試方法。
    # 它的名字，清晰地描述了它的職責。
    def test_start_sentry_creates_pid_file_and_log(self):
        """
        【TDD 核心測試】
        驗證 handle_start_sentry 是否能成功做到：
        1. 創建一個持久化的 PID 戶籍文件。
        2. 戶籍文件的內容是正確的 UUID。
        3. 哨兵工人的日誌中，有它自己打印的「出生證明」。
        """
        # --- 準備階段 (Arrange) ---
        
        # 1. 我們先偽造一個專案數據，加到我們的「沙盒數據庫」裡。
        fake_project_uuid = "uuid-for-start-test"
        fake_project_name = "測試專案"
        # 我們需要一個真實存在的路徑讓哨兵去監控，就用我們沙盒的 temp 目錄好了。
        fake_project_path = self.TEST_TEMP_DIR 
        
        initial_projects = [{
            "uuid": fake_project_uuid,
            "name": fake_project_name,
            "path": fake_project_path,
            "output_file": ["/fake/path.md"]
        }]
        # 我們直接寫入沙盒中的 projects.json 文件。
        with open(self.TEST_PROJECTS_FILE, 'w') as f:
            json.dump(initial_projects, f)

        # --- 執行階段 (Act) ---
        
        # 2. 我們調用我們要測試的目標函式。
        #    我們用 try...except 包裹，是為了防止測試在失敗時直接崩潰。
        try:
            daemon.main_dispatcher(['start_sentry', fake_project_uuid])
        except Exception as e:
            # 如果在啟動過程中發生任何異常，我們用 self.fail() 讓測試立即失敗，並打印出原因。
            self.fail(f"handle_start_sentry 在測試中意外崩潰: {e}")

        # --- 斷言階段 (Assert) ---
        
        # 3. 我們給哨兵一點點時間（例如 0.5 秒），確保它有足夠的時間完成啟動和打印日誌。
        #    這在測試異步或多進程操作時，是一個常見且必要的技巧。
        import time
        time.sleep(0.5)

        # 4. 【斷言一：戶口名簿必須有記錄】
        #    我們斷言 daemon 內存中的 running_sentries 字典，現在應該包含我們剛剛啟動的哨兵。
        self.assertIn(fake_project_uuid, daemon.running_sentries, "哨兵未被記錄到內存中的 running_sentries")
        
        # 5. 我們從戶口名簿中，獲取這個哨兵進程的真實 PID。
        process = daemon.running_sentries[fake_project_uuid]
        pid = process.pid
        
        # 6. 【斷言二：戶籍文件必須存在】
        #    我們構造出預期的戶籍文件路徑。
        pid_file_path = os.path.join(self.TEST_TEMP_DIR, f"{pid}.sentry")
        #    我們用 self.assertTrue() 來斷言這個文件確實存在。
        self.assertTrue(os.path.exists(pid_file_path), f"預期的戶籍文件 {pid_file_path} 未被創建！")

        # 7. 【斷言三：戶籍內容必須正確】
        #    我們讀取戶籍文件的內容。
        with open(pid_file_path, 'r') as f:
            content = f.read()
        #    我們用 self.assertEqual() 來斷言文件內容，與我們預期的 UUID 完全相等。
        self.assertEqual(content, fake_project_uuid, "戶籍文件的內容 (UUID) 不正確！")

        # 8. 【斷言四：出生證明必須存在】
        #    我們構造出預期的日誌文件路徑。
        log_file_path = os.path.join(project_root, 'logs', f"{fake_project_name}.log")
        self.assertTrue(os.path.exists(log_file_path), f"預期的日誌文件 {log_file_path} 未被創建！")
        #    我們讀取日誌文件的內容。
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        #    我們用 self.assertIn() 來斷言「出生證明」的關鍵字，確實出現在了日誌中。
        expected_log_message = f"哨兵工人已啟動。PID: {pid}"
        self.assertIn(expected_log_message, log_content, "日誌文件中未找到哨兵的『出生證明』！")

        # --- 清理階段 (Cleanup) ---
        # 9. 為了不影響下一個測試，我們手動停止這個剛剛啟動的哨兵。
        try:
            daemon.main_dispatcher(['stop_sentry', fake_project_uuid])
        except Exception as e:
            self.fail(f"在測試清理階段，stop_sentry 意外崩潰: {e}")



# 這是一個 Python 的標準寫法。
# 它確保只有當這個文件被直接從命令行執行時，下面的代碼才會運行。
if __name__ == '__main__':
    # unittest.main() 會自動發現這個文件中所有以「test_」開頭的方法，並依次執行它們。
    unittest.main()

