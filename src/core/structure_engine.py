# 我們需要 導入 (import) 一個叫「os」的工具，它能幫助我們處理檔案和路徑。
import os
# 我們需要 導入 (import) 一個叫「sys」的工具，它能幫助我們讀取從外部傳來的指令。
import sys

# 我們用「def」來 定義 (define) 一個我們自己的、全新的遞迴函式。
def generate_tree_recursive(directory, prefix=""):
    """
    這是一個遞迴函式，用於生成目錄樹。
    (v1.0 - 最終版：增加了資料夾斜線和舒適行距)
    """
    # (這部分邏輯我們保留)
    dirs = []
    files = []
    for entry in os.listdir(directory):
        path = os.path.join(directory, entry)
        if os.path.isdir(path):
            dirs.append(entry)
        else:
            files.append(entry)
    entries = sorted(dirs) + sorted(files)
    
    for index, entry in enumerate(entries):
        is_last = (index == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        
        # 我們判斷，如果（if）這一項是一個「資料夾（isdir）」...
        path = os.path.join(directory, entry)
        if os.path.isdir(path):
            # ...我們就在名字後面加上一個斜線「/」。
            entry_name = entry + "/"
        else:
            # 否則，就保持原樣。
            entry_name = entry

        # 我們把「前綴」、「連接符」和「處理後的名字」組合起來，然後「打印（print）」。
        print(f"{prefix}{connector}{entry_name}")
        
        # ---【核心升級 v1.0 - 舒適行距】---
        # 我們準備一個傳遞給下一層的「新前綴」。
        new_prefix = prefix + ("    " if is_last else "│   ")
        
        # 如果（if）這一項不是最後一項...
        if not is_last:
            # ...我們就在它下面，補上一根帶有縮排的「│」連接線，以實現行距。
            print(f"{new_prefix}│")

        if os.path.isdir(path):
            # 我們「呼叫自己」，並把「子資料夾的路徑」和「新前綴」傳遞進去。
            generate_tree_recursive(path, new_prefix)

# 我們用「def」來 定義 (define) 整個程式的「主函式（main）」。
def main():
    """腳本主入口點。"""
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    # ---【核心升級 v1.0 - 根目錄處理】---
    # 我們首先打印出根目錄的名字，並在後面加上斜線。
    print(os.path.basename(root_path) + "/")
    # 然後，為它打印一根起始的「│」連接線。
    print("│")
    
    # 我們呼叫我們的遞迴函式，開始處理根目錄下的內容。
    generate_tree_recursive(root_path)

# 只有當這個腳本被「直接執行」時，才去運行「main()」主函式。
if __name__ == "__main__":
    main()
