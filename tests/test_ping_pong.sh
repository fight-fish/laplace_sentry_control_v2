#!/bin/bash
set -euo pipefail

echo "--- 正在執行第一個契約測試：PING-PONG ---"

# --- 定義變數，讓指令更清晰 ---
DAEMON_SCRIPT="src/core/daemon.py"
EXPECTED_RESPONSE="PONG"

# --- 執行測試 ---
# 1. 呼叫 daemon.py，並傳入 'ping' 指令
# 2. 我們用 $() 這個語法，來捕獲 daemon.py 的所有「標準輸出 (stdout)」
# 3. 將捕獲到的輸出，存儲在 actual_response 這個變數裡
echo "  [測試員]: 正在向廚房發送 'ping' 暗號..."
actual_response=$(python3 "$DAEMON_SCRIPT" ping)
echo "  [廚房]: 回應了: '$actual_response'"

# --- 斷言結果 ---
# 比較「廚房的實際回應」是否等於「我們預期的回應」
if [ "$actual_response" == "$EXPECTED_RESPONSE" ]; then
    echo "✅ PASS: 廚房正確回應了 PONG！第一次握手成功！"
    exit 0 # 成功退出
else
    echo "❌ FAIL: 廚房沒有正確回應 PONG！"
    echo "  [預期]: '$EXPECTED_RESPONSE'"
    echo "  [實際]: '$actual_response'"
    exit 1 # 失敗退出
fi
