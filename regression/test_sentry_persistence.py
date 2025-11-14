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
        
        # 5. 【ADHOC-006 時空校準】
        # 理由：強制將 daemon 的臨時文件目錄，重定向到我們的沙盒中。
        # 這確保了 daemon 創建的 .sentry 文件，會出現在我們的測試可以檢查到的地方。
        daemon.TEMP_DIR = self.TEST_TEMP_DIR

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

    def test_stop_sentry_removes_pid_file(self):
        """
        【TDD 核心測試】
        驗證 handle_stop_sentry 是否能成功做到：
        1. 終止對應的哨兵進程。
        2. 刪除硬盤上對應的 PID 戶籍文件。
        """
        # --- 準備階段 (Arrange) ---
        
        # 1. 我們先執行一次「出生登記」，確保有一個活著的哨兵和一個戶籍文件。
        #    為了不重複代碼，我們直接調用上一個測試，讓它幫我們完成準備工作。
        #    這不是一個標準的單元測試做法，但在這裡，它可以讓我們的邏輯更清晰。
        #    更好的做法是將準備邏輯提取到一個輔助函式中。
        
        # 偽造專案數據
        fake_project_uuid = "uuid-for-stop-test"
        fake_project_path = self.TEST_TEMP_DIR
        initial_projects = [{"uuid": fake_project_uuid, "name": "停止測試專案", "path": fake_project_path, "output_file": ["/fake/path.md"]}]
        with open(self.TEST_PROJECTS_FILE, 'w') as f:
            json.dump(initial_projects, f)

        # 啟動哨兵
        try:
            daemon.main_dispatcher(['start_sentry', fake_project_uuid])
        except Exception as e:
            self.fail(f"在 stop 測試的準備階段，start_sentry 意外崩潰: {e}")

        # 確認哨兵已啟動，並獲取其 PID 和戶籍文件路徑
        self.assertIn(fake_project_uuid, daemon.running_sentries, "準備階段：哨兵未被記錄到內存")
        process = daemon.running_sentries[fake_project_uuid]
        pid = process.pid
        pid_file_path = os.path.join(self.TEST_TEMP_DIR, f"{pid}.sentry")
        self.assertTrue(os.path.exists(pid_file_path), "準備階段：預期的戶籍文件未被創建！")

        # --- 執行階段 (Act) ---
        
        # 2. 我們調用我們要測試的目標函式——「死亡註銷」。
        try:
            daemon.main_dispatcher(['stop_sentry', fake_project_uuid])
        except Exception as e:
            self.fail(f"handle_stop_sentry 在測試中意外崩潰: {e}")

        # --- 斷言階段 (Assert) ---

        # 3. 【斷言一：戶口名簿必須清空】
        #    我們斷言 daemon 內存中的 running_sentries 字典，現在應該已經沒有這個哨兵了。
        self.assertNotIn(fake_project_uuid, daemon.running_sentries, "哨兵記錄未從內存中的 running_sentries 移除")

        # 4. 【斷言二：戶籍文件必須被刪除】
        #    這是我們這次測試的核心！我們期望這個斷言會失敗（紅燈）。
        self.assertFalse(os.path.exists(pid_file_path), f"戶籍文件 {pid_file_path} 在哨兵停止後，依然頑固地存在！")

        # 5. 【斷言三：進程必須被終止】
        #    我們給進程一點點時間來響應終止信號。
        import time
        time.sleep(0.1)
        #    我們斷言進程的 poll() 方法不再返回 None，證明它已經結束了。
        self.assertIsNotNone(process.poll(), f"PID 為 {pid} 的哨兵進程在停止後，依然在運行！")

    def test_list_projects_cleans_up_zombie_pid_files(self):
        """
        【TDD 核心測試】
        驗證 handle_list_projects 是否能自動清理掉無效的「殭屍」戶籍文件。
        """
        # --- 準備階段 (Arrange) ---
        
        # 1. 我們手動在戶籍登記處，創建一個假的、名存實亡的「殭屍戶籍」。
        #    我們使用一個絕對不可能存在的 PID，例如 999999。
        zombie_pid = 999999
        zombie_uuid = "uuid-of-a-zombie-sentry"
        zombie_pid_file_path = os.path.join(self.TEST_TEMP_DIR, f"{zombie_pid}.sentry")
        
        try:
            with open(zombie_pid_file_path, 'w') as f:
                f.write(zombie_uuid)
        except IOError as e:
            self.fail(f"在準備階段，創建殭屍戶籍文件時失敗: {e}")

        # 2. 我們確認一下，這個「殭屍戶籍」現在確實存在於硬盤上。
        self.assertTrue(os.path.exists(zombie_pid_file_path), "準備階段：殭屍戶籍文件未能成功創建！")

        # --- 執行階段 (Act) ---
        
        # 3. 我們調用我們要測試的目標函式——「全國戶籍管理員」。
        #    我們期望它在巡查時，能發現這個 PID 為 999999 的進程根本不存在，
        #    然後主動將其對應的戶籍文件刪除。
        try:
            # 注意：list_projects 會返回一個 JSON 字符串，我們這裡只是調用它，不關心其返回值。
            daemon.main_dispatcher(['list_projects'])
        except Exception as e:
            self.fail(f"handle_list_projects 在測試中意外崩潰: {e}")

        # --- 斷言階段 (Assert) ---

        # 4. 【斷言一：殭屍戶籍必須被清除】
        #    這是我們這次測試的核心！我們期望這個斷言會失敗（紅燈）。
        self.assertFalse(os.path.exists(zombie_pid_file_path), f"殭屍戶籍文件 {zombie_pid_file_path} 在戶籍管理員巡查後，依然陰魂不散！")

    def test_list_projects_recovers_running_state(self):
        """
        【TDD 核心測試】
        驗證 handle_list_projects 在程序「重啟」後，能從硬盤恢復哨兵的運行狀態。
        """
        # --- 準備階段 (Arrange) ---
        
        # 1. 我們先成功啟動一個哨兵，確保它在操作系統中真實運行，並且戶籍文件已創建。
        fake_project_uuid = "uuid-for-recovery-test"
        fake_project_path = self.TEST_TEMP_DIR
        initial_projects = [{"uuid": fake_project_uuid, "name": "狀態恢復測試專案", "path": fake_project_path, "output_file": ["/fake/path.md"]}]
        with open(self.TEST_PROJECTS_FILE, 'w') as f:
            json.dump(initial_projects, f)

        try:
            daemon.main_dispatcher(['start_sentry', fake_project_uuid])
        except Exception as e:
            self.fail(f"在 recovery 測試的準備階段，start_sentry 意外崩潰: {e}")

        # 確認哨兵已在內存和硬盤上都登記成功。
        self.assertIn(fake_project_uuid, daemon.running_sentries, "準備階段：哨兵未被記錄到內存")
        process = daemon.running_sentries[fake_project_uuid]
        pid = process.pid
        pid_file_path = os.path.join(self.TEST_TEMP_DIR, f"{pid}.sentry")
        self.assertTrue(os.path.exists(pid_file_path), "準備階段：預期的戶籍文件未被創建！")

        # 2. 【核心模擬】我們手動清空內存中的「戶口名簿」，模擬程序崩潰重啟。
        #    現在，daemon 的內存裡是空的，但操作系統中，那個哨兵進程依然在頑強地運行著。
        print(f"\n【測試模擬】：正在模擬程序崩潰，手動清空內存中的 running_sentries...")
        daemon.running_sentries.clear()
        self.assertEqual(len(daemon.running_sentries), 0, "模擬崩潰失敗，內存未被清空！")

        # --- 執行階段 (Act) ---
        
        # 3. 我們調用「全國戶籍管理員」，期望它能在此次巡查中，發現那個「有戶籍、有本人，但沒在內存名單上」的合法公民。
        try:
            daemon.main_dispatcher(['list_projects'])
        except Exception as e:
            self.fail(f"handle_list_projects 在測試中意外崩潰: {e}")

        # --- 斷言階段 (Assert) ---

        # 4. 【斷言一：戶籍必須被恢復到內存中】
        #    這是我們這次測試的核心！我們期望這個斷言會失敗（紅燈）。
        self.assertIn(fake_project_uuid, daemon.running_sentries, "程序重啟後，哨兵的運行狀態未能從硬盤恢復到內存中！")
        
        # 5. 【斷言二：恢復的記錄必須正確】
        #    我們進一步檢查，恢復到內存中的，是不是一個正確的 Popen 對象。
        #    注意：我們無法直接比對 Popen 對象，但我們可以檢查它的 PID 是否正確。
        recovered_process = daemon.running_sentries.get(fake_project_uuid)
        self.assertIsNotNone(recovered_process, "恢復的哨兵記錄為 None！")
        # 我們無法直接恢復 Popen 對象，但我們可以檢查恢復的是否是一個包含正確 PID 的記錄。
        # 在未來的重構中，我們可能會將 running_sentries 的結構改為只存儲 PID。
        # 但在當前階段，我們只斷言它被加回來了。
        
        # --- 清理階段 (Cleanup) ---
        # 6. 為了不影響下一個測試，我們手動停止這個哨兵。
        #    注意：現在我們必須依賴我們新寫的、基於文件系統的 stop_sentry。
        try:
            daemon.main_dispatcher(['stop_sentry', fake_project_uuid])
        except Exception as e:
            self.fail(f"在測試清理階段，stop_sentry 意外崩潰: {e}")


# 這是一個 Python 的標準寫法。
# 它確保只有當這個文件被直接從命令行執行時，下面的代碼才會運行。
if __name__ == '__main__':
    # unittest.main() 會自動發現這個文件中所有以「test_」開頭的方法，並依次執行它們。
    unittest.main()

