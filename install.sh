#!/bin/bash
# 我們用 "#!/bin/bash" 來告訴系統，這是一個 Bash 腳本。

# --- 嚴格模式 ---
# 我們用「set -e」來設定一個「安全規則」：
# 如果腳本中的任何一個指令執行失敗了，就立刻停止整個腳本，防止錯誤繼續擴大。
set -e

# --- 腳本主體 ---

# 我們用「echo」指令，在終端「打印」出漂亮的標題，告訴使用者我們正在做什麼。
echo "================================================="
echo "  通用目錄哨兵控制中心 (v2.0) - 一鍵安裝器"
echo "================================================="
echo "" # 打印一個空行，讓格式更好看。


# --- 1. 創建核心目錄結構 ---

echo "--- [1/4] 正在創建『專家分離式』目錄結構..."

# 我們定義一個叫「DIRS_TO_CREATE」的「籃子」，裡面放著所有我們想要創建的資料夾名字。
# 這樣做的好處是，未來如果想增加新目錄，只需要修改這個籃子就行了。
DIRS_TO_CREATE=(
    "src/core"
    "src/shell"
    "data"
    "logs"
    "watchers"
    "backups"
)

# 我們用「for...in...」這個結構，來一個一個地處理「DIRS_TO_CREATE」籃子裡的每一個「目錄（dir）」。
for dir in "${DIRS_TO_CREATE[@]}"; do
    # 我們用「if」來判斷，如果（if）這個目錄「不存在（! -d）」...
    if [ ! -d "$dir" ]; then
    # 我們就用「mkdir -p」指令來「創建目錄（make directory）」。
    # 「-p」參數非常聰明，如果父目錄（如 src）不存在，它會一併創建。
    mkdir -p "$dir"
    echo "    -> 目錄 '$dir/' 已創建。"
    else
    # 如果（else）目錄已經存在了...
    echo "    -> 目錄 '$dir/' 已存在，無需操作。"
    fi
done
echo "--- ✅ 目錄結構創建完畢。"
echo ""


# --- 2. 初始化專案註冊表 (projects.json) ---

echo "--- [2/4] 正在初始化專案註冊表並執行『自我註冊』..."

# 我們定義一個變數，用來存放我們「專案註冊表」的檔案路徑。
PROJECTS_FILE="data/projects.json"

# 我們再次用「if」來判斷，如果（if）註冊表檔案「不存在（! -f）」...
if [ ! -f "$PROJECTS_FILE" ]; then
    # 我們用「cat << EOF > ...」的語法，
    # 來將一大段預設好的文字，直接「寫入（>）」到「projects.json」檔案裡。
    # 這段文字就是我們專案的「自我註冊」訊息。
    cat << EOF > "$PROJECTS_FILE"
[
    {
    "uuid": "laplace-sentry-control-v2-self",
    "name": "laplace_sentry_control_v2 (self-monitoring)",
    "path": ".",
    "md_file": "./README.md",
    "status": "stopped",
    "pid": null
    }
]
EOF
    echo "    -> ✅ 註冊表創建成功，已將本專案作為第一個監控對象。"
else
    echo "    -> 註冊表 '$PROJECTS_FILE' 已存在，無需操作。"
fi
echo "--- ✅ 專案註冊表初始化完畢。"
echo ""


# --- 3. 創建 README.md 指揮中心儀表板 ---

echo "--- [3/4] 正在創建 README.md 指揮中心儀表板..."

# 我們定義一個變數，存放 README 的名字。
README_FILE="README.md"

if [ ! -f "$README_FILE" ]; then
    # 同樣地，我們用「cat << EOF > ...」的語法，把儀表板的模板內容寫入 README。
    cat << EOF > "$README_FILE"
# 通用目錄哨兵控制中心 (Laplace Sentry Control)

本專案旨在打造一個可移植、可擴展的通用開發者文檔自動化工具。

---

## 指揮中心儀表板 (Command Palette)

此處將記錄本專案所有相關的操作指令，以便隨時複製查閱。

### 【第一類：核心執行指令】

*日常使用我們專案的核心功能。*

---

#### 運行主控制台
- **用途：** 啟動交互式主菜單，這是與本系統互動的主要入口。
- **指令：**
    \`\`\`bash
    ./src/shell/control.sh
    \`\`\`

#### 運行一鍵安裝器
- **用途：** 在新環境下，自動完成環境檢查、目錄創建和自我註冊。
- **指令：**
    \`\`\`bash
    ./install.sh
    \`\`\`

---

## 專案結構

<!-- AUTO_TREE_START -->

<!-- 目錄樹將在首次運行更新腳本後，自動生成於此 -->

<!-- AUTO_TREE_END -->

EOF
    echo "    -> ✅ '$README_FILE' 已創建並寫入儀表板模板。"
else
    echo "    -> '$README_FILE' 已存在，無需操作。"
fi
echo "--- ✅ README.md 創建完畢。"
echo ""


# --- 4. 賦予腳本執行權限 ---

echo "--- [4/4] 正在為核心腳本預留執行權限..."

# 我們先用「touch」指令，把未來會用到的腳本的「空檔案」先創建出來。
# 這樣做可以讓我們的安裝腳本更完整，即使現在它們還沒有內容。
touch src/shell/control.sh
touch src/shell/diagnostics.sh
touch src/core/structure_engine.py
touch src/core/path_engine.py

# 我們把所有需要執行權限的腳本，都放進一個叫「SCRIPTS_TO_CHMOD」的籃子裡。
SCRIPTS_TO_CHMOD=(
    "install.sh"
    "src/shell/control.sh"
    "src/shell/diagnostics.sh"
)

# 我們再次用「for...in...」結構，來一個一個地處理籃子裡的每個「腳本（script）」。
for script in "${SCRIPTS_TO_CHMOD[@]}"; do
    # 我們用「chmod +x」指令，來「賦予（change mode）」這個腳本「可執行的（+x）」權限。
    chmod +x "$script"
    echo "    -> 腳本 '$script' 已被賦予執行權限。"
done
echo "--- ✅ 權限設置完畢。"
echo ""


# ... (前面的內容)
echo "================================================="
echo "  🎉 安裝成功！您的專案已準備就緒。"
echo "================================================="

