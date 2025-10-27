# 為了跟你的電腦系統溝通（例如讀取檔案路徑），我們需要 導入（import）一個叫「os」的工具。
import os
# 為了讀取從外部傳進來的指令，我們需要 導入（import）一個叫「sys」的工具。
import sys
# 為了使用「正規表示式」這種強大的文字查找規則，我們需要 導入（import）一個叫「re」的工具。
import re

# 這裡，我們用「def」來 定義（define）一個內部使用的函式，名稱是「_parse_comments」。
# 它的任務是：從一段舊的文字內容中，把之前寫好的註解解析出來。
# 它需要兩個輸入資料：「content_string」（也就是那段包含舊註解的文字）和「root_path」（專案的根目錄路徑）。
def _parse_comments(content_string, root_path):
    # 我們用「if not」來判斷，如果（if）傳入的「content_string」是空的（None 或空字串）...
    if not content_string:
        # ...就直接回傳一個空的結果，避免後續出錯。
        return {}, []  
    # 我們準備一個叫「comments」的有標籤的盒子（{}），用來存放找到的「路徑：註解」配對。
    comments = {}
    # 我們用「re.search」這個功能，在整段文字（content_string）裡尋找被「<!-- AUTO_TREE_START -->」和「<!-- AUTO_TREE_END -->」包住的區塊。
    
    tree_block_match = re.search(r"<!-- AUTO_TREE_START -->(.*?)<!-- AUTO_TREE_END -->", content_string, re.DOTALL)

    # 【核心修正】如果找到了標記，就用標記內的內容；如果沒找到，就把整個輸入字串當作內容。
    if tree_block_match:
        content_to_parse = tree_block_match.group(1)
    else:
        content_to_parse = content_string

    lines = content_to_parse.strip().split('\n')


    # 我們準備一個叫「path_at_indent」的有標籤的盒子（{}），用來記錄每一個「縮排層級」對應的「當前路徑」。
    # -1 層級代表最頂層的「根目錄路徑（root_path）」。
    path_at_indent = {-1: root_path}

    # 我們用「for...in...」這個結構，來一個一個地處理「lines」籃子裡的每一行（line）。
    for line in lines:
        # 我們用「re.search」來檢查這一行（line）是不是一個帶有樹狀結構符號（├── 或 └──）的項目。
        connector_match = re.search(r'(?P<prefix>.*)(├── |└── )(?P<name>.*)', line)
        # 如果（if）這一行不是一個項目...
        if not connector_match:
            # ...就用「continue」跳過，直接處理下一行。
            continue

        # 如果是項目，我們就把符號前面的部分存為「prefix」，符號後面的部分存為「name_part」。
        prefix = connector_match.group('prefix')
        # 我們把「name_part」中「#」註解符號後面的東西去掉，並清除前後的空白和結尾的「/」。
        name_part = connector_match.group('name').split('#', 1)[0].strip().rstrip('/')
        # 如果（if）處理完的「name_part」是空的...
        if not name_part:
            # ...就用「continue」跳過，處理下一行。
            continue

        # 我們計算「prefix」裡面有多少個「│   」或「    」，來判斷這一行的「縮排層級（level）」。
        level = len(re.findall(r'(?:│   |    )', prefix))
        # 我們從「path_at_indent」盒子裡，找出「上一層（level - 1）」的路徑，作為「父層路徑（parent_path）」。
        parent_path = path_at_indent.get(level - 1, root_path)
        # 我們用「os.path.join」把「父層路徑」和「項目名稱」組合起來，得到「當前路徑（current_path）」。
        current_path = os.path.join(parent_path, name_part)
        # 我們把這個新的「層級」和「當前路徑」的配對，記錄到「path_at_indent」盒子裡。
        path_at_indent[level] = current_path

        # 我們用「if」來判斷，如果（if）這一行裡包含「#」註解符號...
        if '#' in line:
            # ...我們就把「#」後面的文字取出來，作為「註解（comment）」。
            comment = line.split('#', 1)[1].strip()
            # 我們計算出相對於「根目錄（root_path）」的「相對路徑（relative_path）」。
            relative_path = os.path.relpath(current_path, root_path)
            # 我們創造一個統一格式的「鑰匙（key）」，例如「./folder/file.txt」。
            key = f"./{relative_path.replace(os.sep, '/')}" if relative_path != '.' else '.'
            # 我們把「鑰匙（key）」和「註解（comment）」這個配對，放進「comments」盒子裡。
            comments[key] = comment
            
    # 最後，回傳裝滿了註解的「comments」盒子和一個目前用不到的空籃子。
    return comments, []

# 這裡，我們用「def」來 定義（define）一個函式，名稱是「_generate_tree」。
# 它的任務是：根據你電腦裡的真實檔案結構，生成一個樹狀圖。
# 它需要一些設定，例如「root_path」（從哪個資料夾開始）、間距和最大深度。
def _generate_tree(root_path, folder_spacing=0, max_depth=None):
    # 我們準備一個叫「lines」的空籃子（[]）來裝樹狀圖的每一行，和一個叫「line_to_path_map」的盒子（{}）來記錄每一行對應的路徑。
    lines, line_to_path_map = [], {}

    # 這裡，我們用「def」來 定義（define）一個只在這裡面使用的「小幫手」函式，叫「recursive_helper」。
    # 「Recursive（遞迴）」的意思是這個函式會呼叫自己，一層一層地深入資料夾。
    def recursive_helper(directory, prefix, relative_path_base, depth):
        # 如果（if）設定了「最大深度（max_depth）」，並且現在的深度（depth）已經達到了...
        if max_depth is not None and depth >= max_depth:
            # ...就用「return」停止，不再往下深入。
            return

        # 我們定義一個叫「exclude_dirs」的集合（set），裡面放著我們不希望顯示在樹狀圖裡的資料夾名稱。
        exclude_dirs = {".git", "__pycache__", "test_scaffold"}
        # 我們用「os.listdir」來獲取資料夾裡所有的檔案和資料夾，只要它們的名字不在「exclude_dirs」裡面。
        items = [name for name in os.listdir(directory) if name not in exclude_dirs]
        # 我們對這些項目進行排序，讓資料夾排在前面，檔案排在後面。
        entries = sorted(items, key=lambda name: (not os.path.isdir(os.path.join(directory, name)), name))

        # 我們用「for...in...」這個結構，來一個一個地處理排序好的項目（entry_name）。
        for i, entry_name in enumerate(entries):
            # 我們判斷這是不是當前資料夾裡的最後一個項目。
            is_last = (i == len(entries) - 1)
            # 我們組合出這個項目的完整路徑。
            path = os.path.join(directory, entry_name)
            # 如果是資料夾，我們就在名字後面加上「/」。
            display_name = entry_name + "/" if os.path.isdir(path) else entry_name
            # 我們把「前綴」和「樹枝符號」和「顯示名稱」組合起來，變成樹狀圖的一行。
            line_content = f"{prefix}{('└── ' if is_last else '├── ')}{display_name}"
            # 把這一行加到（append）我們的「lines」籃子裡。
            lines.append(line_content)
            
            # 我們計算出這個項目對應的「相對路徑」。
            current_relative_path = os.path.join(relative_path_base, entry_name).replace(os.sep, '/')
            # 我們把「行號」和「相對路徑」的配對，記錄到「line_to_path_map」盒子裡。
            line_to_path_map[len(lines) - 1] = current_relative_path

            # 如果（if）這個項目是一個資料夾...
            if os.path.isdir(path):
                # ...我們就準備好給下一層使用的「新前綴（new_prefix）」。
                new_prefix = prefix + ("    " if is_last else "│   ")
                # 然後，我們呼叫「自己（recursive_helper）」，讓它去處理這個子資料夾。
                recursive_helper(path, new_prefix, current_relative_path, depth + 1)
                # 如果（if）設定了「資料夾間距（folder_spacing）」，並且這不是最後一個資料夾，我們就加上一個空白的連接線。
                if folder_spacing > 0 and not is_last:
                    lines.append(prefix + "│   ")

    # 樹狀圖的第一行，是根目錄自己的名字。
    lines.append(os.path.basename(root_path) + "/")
    # 我們記錄下，第 0 行對應的路徑是「.」（代表當前目錄）。
    line_to_path_map[0] = "."
    # 我們開始呼叫「小幫手」函式，讓它從「根目錄（root_path）」開始，建立整個樹狀圖。
    recursive_helper(root_path, "", ".", depth=0)
    # 最後，回傳建立好的「lines」籃子和「line_to_path_map」盒子。
    return lines, line_to_path_map

# 這裡，我們用「def」來 定義（define）一個函式，名稱是「_merge_and_align_comments」。
# 它的任務是：把樹狀圖和註解合併在一起，並且把註解對齊。
def _merge_and_align_comments(tree_lines, line_to_path_map, comments, has_old_content):
    # 我們準備一個「final_lines」的空籃子來裝最終結果，和一個「max_len」變數來記錄最長一行的長度。
    final_lines, max_len = [], 0
    # 我們用「for...in...」結構，先檢查一次所有的樹狀圖行，找出最長的那一行有多長。
    for i, line in enumerate(tree_lines):
        if i in line_to_path_map:
            max_len = max(max_len, len(line.rstrip()))

    # 我們再次用「for...in...」結構，來正式處理每一行。
    for i, line in enumerate(tree_lines):
        # 我們從「line_to_path_map」盒子裡，找出這一行對應的「相對路徑」。
        relative_path = line_to_path_map.get(i)
        # 如果（if）這一行沒有對應的路徑（例如是個空白分隔行）...
        if relative_path is None:
            # ...就直接把它加到「final_lines」籃子裡，然後跳到下一行。
            final_lines.append(line)
            continue
        
        # 我們把這一行內容右邊的空白去掉。
        line_content_part = line.rstrip()
        # 我們去「comments」盒子裡找，看有沒有這個路徑對應的註解。
        comment = comments.get(relative_path)

        # 如果（if）有找到註解...
        if comment:
            # ...我們就計算需要多少個空格來對齊。
            padding = ' ' * (max_len - len(line_content_part) + 2)
            # 然後把「行內容」、「空格」、「#」和「註解」組合起來，加到最終的籃子裡。
            final_lines.append(f"{line_content_part}{padding}# {comment}")
        # 否則（else），如果沒有找到註解...
        else:
            # 我們判斷，如果（if）這是一個更新操作（has_old_content），並且這不是根目錄...
            if has_old_content and relative_path != ".":
                # ...我們就幫它加上一個「# TODO: Add comment here」的提示。
                padding = ' ' * (max_len - len(line_content_part) + 2)
                final_lines.append(f"{line_content_part}{padding}# TODO: Add comment here")
            # 否則（else），如果是第一次生成，或者不需要提示...
            else:
                # ...就直接把原始的行加進去。
                final_lines.append(line)

    # 最後，回傳裝滿了對齊後內容的「final_lines」籃子。
    return final_lines

# 這裡，我們用「def」來 定義（define）一個公開的、可以從外部呼叫的主函式，名稱是「generate_annotated_tree」。
# 它的任務是：整合所有功能，生成一個帶有註解的完整樹狀圖。
# 我們告訴 Python，old_content_string 這個參數，既可能是一個「字串（str）」，也可能是一個「空值（None）」。
def generate_annotated_tree(root_path, old_content_string: str | None = "None", folder_spacing=0, max_depth=None):
    # 我們準備一個空的「comments」盒子和一個空的「orphan_report」籃子。
    comments, orphan_report = {}, []
    # 我們判斷一下，是不是有提供「舊的內容（old_content_string）」。
    has_old_content = old_content_string and old_content_string != "None"

    # 如果（if）有提供舊內容...
    if has_old_content:
        # ...我們就呼叫「_parse_comments」函式，去把舊的註解解析出來。
        comments, orphan_report = _parse_comments(old_content_string, root_path)

    # 接著，我們呼叫「_generate_tree」函式，根據真實檔案系統生成一個新的樹狀圖。
    tree_lines, line_to_path_map = _generate_tree(root_path, folder_spacing=folder_spacing, max_depth=max_depth)
    # 然後，我們呼叫「_merge_and_align_comments」函式，把新的樹狀圖和解析出來的註解合併並對齊。
    final_tree_lines = _merge_and_align_comments(tree_lines, line_to_path_map, comments, has_old_content)
    # 最後，回傳最終的樹狀圖文字和一份報告（目前是空的）。
    return final_tree_lines, orphan_report

# --- 主執行區 (v2.18 智慧讀取版) ---
def main():
    if len(sys.argv) < 2:
        print("【引擎專家錯誤】：至少需要提供一個『專案路徑』參數！", file=sys.stderr)
        sys.exit(1)
        
    project_path = sys.argv[1]
    old_content_source = sys.argv[2] if len(sys.argv) > 2 else None 
    folder_spacing = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    max_depth = int(sys.argv[4]) if len(sys.argv) > 4 else None

    old_content = None
    
    # 【核心修正】我們現在要判斷 old_content_source 的三種可能性
    if old_content_source == "-":
        # 1. 如果是 "-", 從標準輸入讀取
        old_content = sys.stdin.read()
    elif old_content_source and os.path.isfile(old_content_source):
        # 2. 如果是一個存在的檔案路徑，就讀取該檔案的內容
        try:
            with open(old_content_source, 'r', encoding='utf-8') as f:
                old_content = f.read()
        except Exception as e:
            print(f"【引擎專家錯誤】：讀取舊內容檔案 '{old_content_source}' 時出錯！\n  -> {e}", file=sys.stderr)
            sys.exit(3)
    else:
        # 3. 否則，就把它當作普通的字串內容
        old_content = old_content_source

    final_lines, _ = generate_annotated_tree(
        project_path, 
        old_content, 
        folder_spacing=folder_spacing, 
        max_depth=max_depth
    )
    
    for line in final_lines:
        print(line)


if __name__ == "__main__":
    main()



