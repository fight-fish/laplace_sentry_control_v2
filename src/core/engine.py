# 為了跟你的電腦系統溝通（例如讀取檔案路徑），我們需要 導入（import）一個叫「os」的工具。
import os
# 為了讀取從外部傳進來的指令，我們需要 導入（import）一個叫「sys」的工具。
import sys
# 為了使用「正規表示式」這種強大的文字查找規則，我們需要 導入（import）一個叫「re」的工具。
import re

# ==============================================================================
# 【v4.0 心臟移植手術】 - 註釋解析器 (回歸 v0 智慧)
# ==============================================================================
# 我們用「def」來 定義（define）一個內部使用的函式，名稱是「_parse_comments」。
# 它的任務是：從一段舊的文字內容中，把之前寫好的註解解析出來。
def _parse_comments(content_string):
    """
    【v4.0 - 回歸 v0 智慧】
    使用最簡單、最可靠的「視覺匹配」策略來解析註解。
    - Key:   整行的、不包含註解的、帶有樹狀符號的視覺路徑 (例如: '├── src/')
    - Value: 註解內容 (例如: '【源碼區】...')
    這個策略雖然脆弱（依賴視覺格式不變），但它杜絕了所有因「相對路徑計算」
    而引發的、無法預測的、災難性的靜默失敗。
    """
    if not content_string:
        return {}
    
    comments = {}
    
    # 1. 自己從完整的原始文件中，提取乾淨的 tree_block。
    tree_block_match = re.search(r"<!-- AUTO_TREE_START -->(.*?)<!-- AUTO_TREE_END -->", content_string, re.DOTALL)
    if not tree_block_match:
        return {}

    tree_block_raw = tree_block_match.group(1).strip()
    if tree_block_raw.startswith("```") and tree_block_raw.endswith("```"):
        content_to_parse = tree_block_raw[3:-3].strip()
    else:
        content_to_parse = tree_block_raw

    # 2. 逐行進行視覺匹配
    for line in content_to_parse.split('\n'):
        # 我們只關心那些包含了註解符號 '#' 的行
        if '#' in line:
            # 我們用 rsplit('#', 1) 這個精準的方法，從右邊開始，只切一刀
            # 這樣就完美地將「視覺路徑部分」和「註解部分」分開了
            parts = line.rsplit('#', 1)
            if len(parts) == 2:
                # Key 就是左邊的視覺路徑，並去掉尾部多餘的空格
                path_part = parts[0].rstrip()
                # Value 就是右邊的註解內容
                comment_part = parts[1].strip()
                
                # 只有當 path_part 和 comment_part 都不是空的，我們才把它存起來
                if path_part and comment_part:
                    comments[path_part] = comment_part
                    
    return comments


# ==============================================================================
#  【v4.0 心臟移植手術】 - 結構生成器 (保持不變，維持視覺穩定)
# ==============================================================================
# 這裡，我們用「def」來 定義（define）一個函式，名稱是「_generate_tree」。
# 它的任務是：根據你電腦裡的真實檔案結構，生成一個樹狀圖。
def _generate_tree(root_path, folder_spacing=0, max_depth=None):
    # 我們準備一個叫「lines」的空籃子（[]）來裝樹狀圖的每一行。
    # 【核心改變】我們不再需要 line_to_path_map 這個複雜的地圖了！
    lines = []

    def recursive_helper(directory, prefix, depth):
        if max_depth is not None and depth >= max_depth:
            return

        exclude_dirs = {".git", "__pycache__", "test_scaffold", "_archive"}
        try:
            items = [name for name in os.listdir(directory) if name not in exclude_dirs]
        except FileNotFoundError:
            # 如果在遞迴過程中，某個子目錄找不到了，就打印一個警告，然後優雅地跳過。
            print(f"【引擎警告】：在生成目錄樹時，找不到子目錄 '{directory}'，已跳過。", file=sys.stderr)
            return
            
        entries = sorted(items, key=lambda name: (not os.path.isdir(os.path.join(directory, name)), name))

        for i, entry_name in enumerate(entries):
            is_last = (i == len(entries) - 1)
            path = os.path.join(directory, entry_name)
            display_name = entry_name + "/" if os.path.isdir(path) else entry_name
            line_content = f"{prefix}{('└── ' if is_last else '├── ')}{display_name}"
            lines.append(line_content)
            
            if os.path.isdir(path):
                new_prefix = prefix + ("    " if is_last else "│   ")
                recursive_helper(path, new_prefix, depth + 1)
                if folder_spacing > 0 and not is_last:
                    lines.append(prefix + "│   ")

    lines.append(os.path.basename(root_path) + "/")
    recursive_helper(root_path, "", depth=0)
    return lines


# ==============================================================================
# 【v4.0 心臟移植手術】 - 註解合併器 (回歸 v0 智慧)
# ==============================================================================
# 這裡，我們用「def」來 定義（define）一個函式，名稱是「_merge_and_align_comments」。
# 它的任務是：把樹狀圖和註解合併在一起，並且把註解對齊。
def _merge_and_align_comments(tree_lines, comments):
    """
    【v4.0 - 回歸 v0 智慧】
    使用「視覺匹配」策略來合併註解。
    """
    final_lines = []
    
    # 1. 測量所有行中，最長的那一行的長度，為對齊做準備。
    max_len = 0
    for line in tree_lines:
        # 我們只測量那些看起來像是「內容」的行
        if '──' in line:
            max_len = max(max_len, len(line.rstrip()))

    # 2. 逐行進行合併
    for line in tree_lines:
        # Key 就是當前這一行去掉尾部空格後的樣子
        stripped_line = line.rstrip()
        
        # 我們用這個視覺 Key，去註解字典裡查找
        comment = comments.get(stripped_line)

        if comment:
            # 如果找到了，就計算填充空格，然後組合起來
            padding = ' ' * (max_len - len(stripped_line) + 2)
            final_lines.append(f"{stripped_line}{padding}# {comment}")
        else:
            # 如果沒找到，我們判斷一下：
            # 只有當這一行是「內容行」時，才給它加上 TODO
            if '──' in line:
                padding = ' ' * (max_len - len(stripped_line) + 2)
                final_lines.append(f"{stripped_line}{padding}# TODO: Add comment here")
            else:
                # 否則（比如是個空行），就保持原樣
                final_lines.append(line)

    return final_lines


# ==============================================================================
# 【v4.0 心臟移植手術】 - 總裝配線 (邏輯簡化)
# ==============================================================================
# 這裡，我們用「def」來 定義（define）一個公開的、可以從外部呼叫的主函式，名稱是「generate_annotated_tree」。
# 它的任務是：整合所有功能，生成一個帶有註解的完整樹狀圖。
def generate_annotated_tree(root_path, old_content_string: str | None = "None", folder_spacing=0, max_depth=None):
    
    # 1. 調用【v4.0 解析器】，傳入完整的舊內容，拿到註解字典。
    comments = _parse_comments(old_content_string)

    # 2. 調用【保持不變的生成器】，拿到純淨的、視覺完美的目錄樹行列表。
    tree_lines = _generate_tree(root_path, folder_spacing=folder_spacing, max_depth=max_depth)
    
    # 3. 調用【v4.0 合併器】，把新的樹狀圖和解析出來的註解合併並對齊。
    final_tree_lines = _merge_and_align_comments(tree_lines, comments)
    
    # 我們用「\n」（換行符）把籃子裡的所有行，連接（join）成一大段完整的文字。
    return "\n".join(final_tree_lines)


# ==============================================================================
#  主執行區 (保持不變)
# ==============================================================================
def main():
    if len(sys.argv) < 2:
        print("【引擎專家錯誤】：至少需要提供一個『專案路徑』參數！", file=sys.stderr)
        sys.exit(1)
        
    project_path = sys.argv[1]
    old_content_source = sys.argv[2] if len(sys.argv) > 2 else None 
    folder_spacing = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    max_depth = int(sys.argv[4]) if len(sys.argv) > 4 else None

    old_content = None
    
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
        old_content = old_content_source

    final_tree = generate_annotated_tree(
        project_path, 
        old_content, 
        folder_spacing=folder_spacing, 
        max_depth=max_depth
    )
    
    print(final_tree)


if __name__ == "__main__":
    main()
