
#!/bin/bash
# ==============================================================================
#  極簡驗收腳本 (verify.sh)
#  目標：用最簡單、最可靠的方式，驗證 engine.py 的核心功能。
# ==============================================================================

# --- 準備一個乾淨的實驗室 ---
# 我們在 /tmp 這個公共臨時文件夾裡進行所有操作，完全不影響我們的專案目錄
LAB_PATH="/tmp/verify_lab"
rm -rf "$LAB_PATH"
mkdir -p "$LAB_PATH/src"
touch "$LAB_PATH/README.md"

# --- 準備一份帶有「舊註解」的參考文件 ---
# 我們用 cat 指令，在 Linux 環境中直接生成這個文件，確保它的換行符是正確的 LF (\n)
OLD_CONTENT_FILE="$LAB_PATH/old_readme.md"
cat <<'EOF' > "$OLD_CONTENT_FILE"
<!-- AUTO_TREE_START -->

/tmp/verify_lab/
├── src/       # 【源碼區】
└── README.md  # 【說明書】

<!-- AUTO_TREE_END -->
EOF

# --- 正式執行驗收 ---
echo "--- 正在呼叫「引擎專家 (engine.py)」---"
echo "我們將讓它掃描實驗室目錄: $LAB_PATH"
echo "並參考這份舊文件裡的註解: $OLD_CONTENT_FILE"
echo "--------------------------------------------------"

# 呼叫 python 專家，讓它掃描 LAB_PATH，並參考 OLD_CONTENT_FILE
# 我們把專家的輸出結果，存儲在一個變數裡
ACTUAL_RESULT=$(python3 src/core/engine.py "$LAB_PATH" "$OLD_CONTENT_FILE")

# --- 打印驗收結果 ---
echo "✅ 「引擎專家」執行完畢，這是它生成的最終結果："
echo ""
echo "$ACTUAL_RESULT"
echo ""
echo "--------------------------------------------------"
echo "請您親眼驗收，以上結果中的註解（# 【源碼區】和 # 【說明書】）是否被正確保留了？"

