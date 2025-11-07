# src/core/engine.py

# 我們需要導入（import）幾個 Python 內建的標準工具：
import os       # 用於與「作業系統（os）」互動，如遍歷目錄。
import sys      # 用於讀取「系統（sys）」參數和控制腳本退出。
import re       # 用於執行強大的「正規表達式（re）」匹配。

# ==============================================================================
# 【v4.0 核心演算法】 - 註釋解析器 (回歸 v0 智慧)
# ==============================================================================

# 我們用「def」來 定義（define）一個內部使用的函式，名稱是「_parse_comments」。
# 它的任務是：從一段舊的文字內容中，把之前寫好的註解解析出來，存入一個字典。
def _parse_comments(content_string):
    """
    【v4.0 - 回歸 v0 智慧】
    使用最簡單、最可靠的「視覺匹配」策略來解析註解。
    - Key:   整行的、不包含註解的、帶有樹狀符號的視覺路徑 (例如: '├── src/')
    - Value: 註解內容 (例如: '【源碼區】...')
    COMPAT: 這個策略雖然在面對格式變動時比較脆弱，但它從根本上杜絕了所有因「相對路徑計算」
    而引發的、災難性的靜默失敗（參考日誌 025）。這是為了穩定性而做出的關鍵妥協。
    """
    # DEFENSE: 如果傳入的內容是空的，就直接返回一個空字典。
    if not content_string:
        return {}

    comments = {}

    # 1. 我們用正規表達式，從完整的原始文件中，精準地提取出被標記包裹的目錄樹區塊。
    tree_block_match = re.search(r"<!-- AUTO_TREE_START -->(.*?)<!-- AUTO_TREE_END -->", content_string, re.DOTALL)
    if not tree_block_match:
        return {} # 如果連標記都找不到，就沒什麼可解析的了。

    # HACK: 處理被 Obsidian 等工具自動包裹的 ` ``` ` 代碼塊。
    # 我們需要先「拆掉」這個外包裝，才能拿到純淨的目錄樹內容。
    tree_block_raw = tree_block_match.group(1).strip()
    if tree_block_raw.startswith("```") and tree_block_raw.endswith("```"):
        content_to_parse = tree_block_raw[3:-3].strip()
    else:
        content_to_parse = tree_block_raw

    # 2. 我們用「for...in...」結構，來逐行處理我們拿到的純淨目錄樹。
    for line in content_to_parse.split('\n'):
        # 我們只關心那些包含了註解符號 '#' 的行。
        if '#' in line:
            # 我們用 rsplit('#', 1) 這個精準的方法，從右邊開始，只切一刀。
            # 這能完美地將「視覺路徑部分」和「註解部分」分開，即使註解本身也包含'#'。
            parts = line.rsplit('#', 1)
            if len(parts) == 2:
                # Key 就是左邊的視覺路徑，並用 rstrip() 去掉尾部多餘的空格。
                path_part = parts[0].rstrip()
                # Value 就是右邊的註解內容，並用 strip() 去掉頭尾空格。
                comment_part = parts[1].strip()

                # DEFENSE: 只有當路徑和註解都不是空的，我們才認為這是一條有效的記錄。
                if path_part and comment_part:
                    comments[path_part] = comment_part

    return comments

# ==============================================================================
#  【v4.0 核心演算法】 - 結構生成器 (視覺穩定性優先)
# ==============================================================================

# 這裡，我們用「def」來 定義（define）一個函式，名稱是「_generate_tree」。
# 它的任務是：根據你電腦裡的真實檔案結構，生成一個視覺上穩定、準確的樹狀圖。
def _generate_tree(root_path, folder_spacing=0, max_depth=None):
    # 我們準備一個叫「lines」的空列表（list），用來收集樹狀圖的每一行。
    lines = []

    # 我們在函式內部，又定義（define）了一個遞迴輔助函式「recursive_helper」。
    # 這是實現目錄遍歷的核心。
    def recursive_helper(directory, prefix, depth):
        # 如果達到了最大深度限制，就停止遞迴。
        if max_depth is not None and depth >= max_depth:
            return

        # 我們定義一個要排除的目錄集合（set），以提高效率和整潔度。
        exclude_dirs = {".git", "__pycache__", "test_scaffold", "_archive", ".venv", ".vscode"}
        try:
            # 我們用「列表推導式」來獲取目錄下的所有項目，並過濾掉要排除的。
            items = [name for name in os.listdir(directory) if name not in exclude_dirs]
        except FileNotFoundError:
            # DEFENSE: 如果在遞迴過程中，某個子目錄突然消失了，我們不能讓整個程式崩潰。
            print(f"【引擎警告】：在生成目錄樹時，找不到子目錄 '{directory}'，已跳過。", file=sys.stderr)
            return

        # 我們對項目進行排序，確保每次生成的順序都一樣。
        # 排序規則是：資料夾優先，然後按字母順序。
        entries = sorted(items, key=lambda name: (not os.path.isdir(os.path.join(directory, name)), name))

        for i, entry_name in enumerate(entries):
            is_last = (i == len(entries) - 1)
            path = os.path.join(directory, entry_name)
            # 如果是目錄，就在名字後面加上 "/"。
            display_name = entry_name + "/" if os.path.isdir(path) else entry_name
            # 根據是否是最後一個項目，選擇不同的樹狀符號。
            line_content = f"{prefix}{('└── ' if is_last else '├── ')}{display_name}"
            lines.append(line_content)

            if os.path.isdir(path):
                # 為了保持視覺上的連續性，我們計算下一層遞迴需要的前綴。
                new_prefix = prefix + ("    " if is_last else "│   ")
                # 進行遞迴調用。
                recursive_helper(path, new_prefix, depth + 1)
                # FUTURE: 這是為了未來可能增加的「資料夾間距」功能預留的。
                if folder_spacing > 0 and not is_last:
                    lines.append(prefix + "│   ")

    # 我們將根目錄本身作為樹的第一行。
    lines.append(os.path.basename(root_path) + "/")
    # 開始遞迴。
    recursive_helper(root_path, "", depth=0)
    return lines

# ==============================================================================
# 【v4.0 核心演算法】 - 註解合併器 (回歸 v0 智慧)
# ==============================================================================

# 這裡，我們用「def」來 定義（define）一個函式，名稱是「_merge_and_align_comments」。
# 它的任務是：把新生成的樹狀圖和從舊內容中解析出的註解，合併在一起並對齊。
def _merge_and_align_comments(tree_lines, comments):
    """
    【v4.0 - 回歸 v0 智慧】
    使用「視覺匹配」策略來合併註解。
    """
    final_lines = []

    # 1. 我們先遍歷一次所有行，測量出最長的那一行的長度，這是為了後續的對齊。
    max_len = 0
    for line in tree_lines:
        # 我們只測量那些看起來像是「內容」的行（包含樹狀符號）。
        if '──' in line:
            max_len = max(max_len, len(line.rstrip()))

    # 2. 我們再次遍歷所有行，這次是為了進行合併。
    for line in tree_lines:
        # 我們用當前這一行去掉尾部空格後的樣子，作為去註解字典裡查找的 Key。
        stripped_line = line.rstrip()

        # 我們用字典的 .get() 方法來查找註解，如果找不到，它會安全地返回 None。
        comment = comments.get(stripped_line)

        if comment:
            # 如果找到了註解，我們就計算需要填充多少空格來實現對齊。
            padding = ' ' * (max_len - len(stripped_line) + 2)
            # 然後將「行內容 + 填充空格 + # + 註解」拼接起來。
            final_lines.append(f"{stripped_line}{padding}# {comment}")
        else:
            # 如果沒找到註解，我們需要判斷一下。
            # 只有當這一行是「內容行」時，我們才給它加上一個 TODO 標記。
            if '──' in line:
                padding = ' ' * (max_len - len(stripped_line) + 2)
                # TODO: 這裡的提示文字未來可以做成可配置的。
                final_lines.append(f"{stripped_line}{padding}# TODO: Add comment here")
            else:
                # 否則（比如是個用於間隔的空行），就保持原樣。
                final_lines.append(line)

    return final_lines

# ==============================================================================
# 【v4.0 核心演算法】 - 總裝配線 (Public API)
# ==============================================================================

# 這裡，我們用「def」來 定義（define）一個公開的、可以從外部調用的主函式。
# 它的任務是：按順序調用所有內部函式，完成一次完整的生成流程。
def generate_annotated_tree(root_path, old_content_string: str | None = "None", folder_spacing=0, max_depth=None):

    # 1. 調用【v4.0 解析器】，傳入完整的舊內容，拿到註解字典。
    comments = _parse_comments(old_content_string)

    # 2. 調用【結構生成器】，拿到純淨的、視覺完美的目錄樹行列表。
    tree_lines = _generate_tree(root_path, folder_spacing=folder_spacing, max_depth=max_depth)

    # 3. 調用【v4.0 合併器】，把新的樹狀圖和解析出來的註解合併並對齊。
    final_tree_lines = _merge_and_align_comments(tree_lines, comments)

    # 我們用「\n」（換行符）把列表中的所有行，連接（join）成一大段完整的文字，並返回。
    return "\n".join(final_tree_lines)

# ==============================================================================
#  主執行區 (Command-Line Interface)
# ==============================================================================
def main():
    """定義並執行程式的命令列介面。"""
    # DEFENSE: 檢查傳入的參數數量是否足夠。
    if len(sys.argv) < 2:
        print("【引擎專家錯誤】：至少需要提供一個『專案路徑』參數！", file=sys.stderr)
        sys.exit(1)

    project_path = sys.argv[1]
    # 我們用一個三元表達式來安全地獲取第二個參數。
    old_content_source = sys.argv[2] if len(sys.argv) > 2 else None
    folder_spacing = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    max_depth = int(sys.argv[4]) if len(sys.argv) > 4 else None

    old_content = None

    # HACK: 這裡的邏輯是為了讓引擎能同時處理兩種輸入源：
    # 1. 從管道傳來的標準輸入 (`-`)
    # 2. 一個檔案路徑
    if old_content_source == "-":
        old_content = sys.stdin.read()
    elif old_content_source and os.path.isfile(old_content_source):
        try:
            with open(old_content_source, 'r', encoding='utf-8') as f:
                old_content = f.read()
        except Exception as e:
            print(f"【引擎專家錯誤】：讀取舊內容檔案 '{old_content_source}' 時出錯！\n  -> {e}", file=sys.stderr)
            sys.exit(3)
    else:
        # 如果既不是 `-` 也不是有效檔案，就直接把參數本身當作內容。
        old_content = old_content_source

    # 調用我們的「總裝配線」函式來生成最終的目錄樹。
    final_tree = generate_annotated_tree(
        project_path,
        old_content,
        folder_spacing=folder_spacing,
        max_depth=max_depth
    )

    # 將結果打印到標準輸出。
    print(final_tree)

# 這是一個 Python 的標準寫法。
# 它確保只有當這個文件被直接執行時，main() 函式才會被調用。
if __name__ == "__main__":
    main()
