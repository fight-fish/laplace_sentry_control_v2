# tests/test_multiprocessing_communication.py

# 我們需要 導入（import）一系列 Python 內建的工具。
import multiprocessing
import time
import os

# ==============================================================================
#  子進程執行的任務 (The Child's Task)
# ==============================================================================
# 我們用「def」來 定義（define）一個函式，這就是子進程要執行的全部工作。
# 它接收兩個參數：一個是我們共享的「狀態字典」，另一個是它自己的「身份ID」。
def child_process_task(shared_status_dict, child_id):
    """
    這是一個模擬哨兵工人的極簡任務。
    """
    # 為了方便觀察，我們讓它先打印一條「出生證明」。
    print(f"[子進程 {child_id}]：我出生了！我的 PID 是 {os.getpid()}。")

    # 模擬工作：子進程會嘗試修改共享字典中的內容。
    try:
        # 它在字典中，用自己的 ID 作為鑰匙，寫入一個表示「正在運行」的狀態。
        shared_status_dict[child_id] = 'RUNNING'
        print(f"[子進程 {child_id}]：我已將我的狀態更新為 RUNNING。")

        # 模擬一段工作時間。
        time.sleep(3)

        # 工作完成後，它再次更新自己的狀態為「已完成」。
        shared_status_dict[child_id] = 'COMPLETED'
        print(f"[子進程 {child_id}]：任務完成，我將狀態更新為 COMPLETED。")

    except Exception as e:
        # 如果在工作中發生任何意外，它會嘗試在字典中記錄錯誤。
        shared_status_dict[child_id] = f'ERROR: {e}'
        print(f"[子進程 {child_id}]：發生了致命錯誤！ {e}")

    # 子進程打印「遺言」並自然死亡。
    print(f"[子進程 {child_id}]：我的任務結束了，再見。")


# ==============================================================================
#  主進程（父進程）的協調邏輯 (The Parent's Logic)
# ==============================================================================
# 這是一個 Python 的標準寫法，確保只有當這個文件被直接執行時，下面的程式碼才會運行。
if __name__ == "__main__":
    print(f"[主進程]：大家好，我是主進程，我的 PID 是 {os.getpid()}。")
    print("[主進程]：我即將創建一個『共享狀態字典』和一個子進程。")

    # --- 核心準備工作 ---
    # 1. 我們創建一個「管理器（Manager）」，它像一個工頭，負責管理共享資源。
    with multiprocessing.Manager() as manager:
        
        # 2. 我們讓「工頭」為我們創建一個可以在多個進程之間安全共享的「字典（dict）」。
        shared_dict = manager.dict()
        print(f"[主進程]：共享字典已創建。初始內容: {dict(shared_dict)}")

        # 3. 我們定義子進程的身份 ID。
        child_id = 'sentry_worker_001'

        # --- 啟動子進程 ---
        # 我們創建一個「進程（Process）」對象。
        # target=child_process_task 指定了子進程要去執行的函式。
        # args=(shared_dict, child_id) 告訴它需要帶上「共享字典」和「身份ID」這兩個「工具」去工作。
        p = multiprocessing.Process(target=child_process_task, args=(shared_dict, child_id))

        # 命令子進程開始工作！
        p.start()
        print(f"[主進程]：已啟動子進程 (PID: {p.pid})。")

        # --- 主進程的監控循環 ---
        print("[主進程]：我將每秒檢查一次共享字典的內容...")
        # 我們讓主進程也監控 5 秒鐘。
        for i in range(5):
            time.sleep(1)
            # 我們直接讀取共享字典的當前內容。
            # dict() 只是為了讓打印出來的格式更漂亮。
            current_status = dict(shared_dict)
            print(f"  [監控中 - 第 {i+1} 秒] 共享狀態為: {current_status}")

        # --- 等待並驗收 ---
        # 主進程會在這裡「等待」子進程完成它的所有工作。
        p.join()
        print("[主進程]：子進程已結束工作。")

        # --- 最終驗收 ---
        print("\n" + "="*20 + " 最終驗收 " + "="*20)
        final_status = dict(shared_dict)
        print(f"[主進程]：子進程結束後，共享字典的最終內容是: {final_status}")

        # 這是我們實驗的最終評判標準！
        expected_final_value = 'COMPLETED'
        actual_final_value = final_status.get(child_id)

        if actual_final_value == expected_final_value:
            print("\033[92m[✓] 測試通過！主進程成功讀取到了子進程寫入的最終狀態。\033[0m")
        else:
            print("\033[91m[✗] 測試失敗！未能讀取到預期的最終狀態。\033[0m")
            print(f"    - 預期狀態: '{expected_final_value}'")
            print(f"    - 實際狀態: '{actual_final_value}'")
        print("="*52)

