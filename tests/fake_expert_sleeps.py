# tests/fake_expert_sleeps.py
import time
import sys

# 我們打印一條日誌，證明這個假專家被成功調用了。
print("【假專家】：我收到了工作指令，準備開始睡覺...", file=sys.stderr)

# 讓這個腳本暫停執行 20 秒，以模擬一個耗時極長的任務。
time.sleep(20)

# 睡醒後，打印一條日誌。
print("【假專家】：啊...睡得真好，我現在要報告工作完成了。", file=sys.stderr)

# 像一個正常的專家一樣，向標準輸出打印一些結果。
print("DONE")

# 以成功的退出碼 0 退出。
sys.exit(0)
