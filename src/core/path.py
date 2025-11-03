# 為了與「作業系統（os）」互動、讀取「系統（sys）」參數、
# 使用「正規表達式（re）」和解析「命令列參數（argparse）」，
# 我們需要先 導入（import）這些工具。
import os
import sys
import argparse
import re

# --- 核心路徑處理函式 ---

# 我們用「def」來 定義（define）一個名叫「normalize_path」的函式。
# 這是我們「尋路專家」最核心的「翻譯」能力。
# 在 src/core/path.py 中

def normalize_path(path_str):
    """
    將各種平台、各種格式的原始路徑字串，標準化為統一的、在 WSL 中可用的 Linux 路徑格式。
    【v2.4 穩定版】—— 支援 //wsl.localhost 與 /wsl.localhost 兩種格式
    """
    if not isinstance(path_str, str):
        return ""
    
    p = path_str.strip()
    while p.startswith(('"', "'")) and p.endswith(('"', "'")):
        p = p[1:-1].strip()
    
    p = p.replace("\\", "/")
    
    # ✅ 同時匹配一或兩個斜線開頭的 wsl.localhost
    match_wsl = re.match(r"^/{1,2}wsl\.localhost/([^/]+)/(.*)", p, re.IGNORECASE)
    if match_wsl:
        p = "/" + match_wsl.group(2)
        
    match_drive = re.match(r"([A-Za-z]):/(.*)", p)
    if match_drive:
        drive_letter = match_drive.group(1).lower()
        rest_of_path = match_drive.group(2)
        p = f"/mnt/{drive_letter}/{rest_of_path}"
        
    p = re.sub(r"/{2,}", "/", p)
    return p



# 在 src/core/path.py 中，normalize_path 函式的下方

# 我們用「def」來 定義（define）一個新的、可以被其他 Python 腳本導入的函式。
# 它的任務是：檢查傳入的路徑列表是否都真實存在。
def validate_paths_exist(paths_to_check):
    """
    這是一個可導入的函式，檢查路徑列表是否存在。
    它會直接返回 True (代表全部存在) 或 False (代表至少有一個不存在)。
    """
    # 我們用「for...in...」這個結構，來一個一個地檢查傳入的「路徑列表（paths_to_check）」。
    for path in paths_to_check:
        # 我們用「os.path.exists()」來判斷，如果（if not）這個路徑「不存在（exists）」...
        if not os.path.exists(path):
            # 就立刻返回（return）一個代表「失敗」的布林值 False。
            return False
    # 如果循環順利跑完（代表所有路徑都存在），就返回（return）一個代表「成功」的布林值 True。
    return True


#  -----------------------------------------------------------------------
# --- 核心命令處理函式 (Handler Functions) ---
#  -----------------------------------------------------------------------


# 我們用「def」來 定義（define）一個專門處理「讀取」命令的函式。
def handle_read(filepath):
    # 我們用「if not os.path.isfile()」來判斷，如果（if）這個「檔案路徑（filepath）」不是一個存在的「檔案（file）」...
    if not os.path.isfile(filepath):
        # 我們就「打印（print）」一條錯誤訊息到「標準錯誤流（stderr）」。
        print(f"【尋路專家錯誤】：要讀取的檔案不存在！\n  -> {filepath}", file=sys.stderr)
        # 然後用「sys.exit(2)」指令，帶著一個代表「路徑錯誤」的退出碼「2」，立刻「退出（exit）」腳本。
        sys.exit(2)
    # 我們用「try...except...」這個結構，來「嘗試（try）」執行可能會出錯的程式碼。
    try:
        # 「with open(...)」是一個安全的讀取檔案的方式。
        with open(filepath, 'r', encoding='utf-8') as f:
            # 【核心修正】我們只做一件事：讀取檔案的「全部內容（content）」，然後「打印（print）」出來。
            # 不再做任何尋找標記或切片的額外處理。
            print(f.read())
        # 如果一切順利，就用「sys.exit(0)」，帶著代表「成功」的退出碼「0」，「退出（exit）」腳本。
        sys.exit(0)
    # 如果在「嘗試（try）」的過程中，發生了任何「異常（Exception）」...
    except Exception as e:
        # 我們就把這個「異常（e）」的內容打印出來，並帶著退出碼「3」（代表其他錯誤）退出。
        print(f"【尋路專家錯誤】：讀取檔案 '{filepath}' 時發生未知錯誤！\n  -> {e}", file=sys.stderr)
        sys.exit(3)


# 我們用「def」來 定義（define）一個專門處理「寫入」命令的函式。
def handle_write(filepath):
    # 【v2.0 管道兼容版】不再接收 content 參數，而是從標準輸入讀取
    parent_dir = os.path.dirname(filepath)
    if parent_dir and not os.path.isdir(parent_dir):
        print(f"【尋路專家錯誤】：要寫入的目標檔案所在的資料夾不存在！\n  -> {parent_dir}", file=sys.stderr)
        sys.exit(2)
    try:
        # 從標準輸入讀取所有要寫入的內容
        content_to_write = sys.stdin.read()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_to_write)
        sys.exit(0)
    except Exception as e:
        print(f"【尋路專家錯誤】：寫入檔案 '{filepath}' 時發生未知錯誤！\n  -> {e}", file=sys.stderr)
        sys.exit(3)



# 我們用「def」來 定義（define）一個專門處理「驗證」命令的函式。
def handle_validate(paths):
    # 【改造點】這個為命令行服務的函式，現在去呼叫（call）我們剛剛創建的新函式。
    if not validate_paths_exist(paths):
        # 如果（if not）新函式返回了 False，我們就在這裡打印錯誤訊息，並帶著退出碼「2」退出。
        print(f"【尋路專家錯誤】：一個或多個路徑不存在或無效。", file=sys.stderr)
        sys.exit(2)
    # 如果新函式返回了 True，我們就什麼都不打印，並帶著退出碼「0」（代表成功）安靜地退出。
    sys.exit(0)



# --- 主執行區：命令列介面設定 ---

# 我們用「def」來 定義（define）一個名叫「main」的主函式。
def main():
    # 1. 我們用「argparse.ArgumentParser」來創建一個「總翻譯官（parser）」。
    parser = argparse.ArgumentParser(
        description="路徑與 I/O 專家：負責所有檔案的讀、寫、驗證操作。",
        formatter_class=argparse.RawTextHelpFormatter # 這個選項能讓幫助訊息保持我們寫的格式
    )
    # 2. 我們告訴「總翻譯官」，它下面可以有多個「子翻譯官（subparsers）」。
    subparsers = parser.add_subparsers(dest='command', required=True, help='可執行的命令')

    # 3. 定義「read」這個「子翻譯官」。
    parser_read = subparsers.add_parser('read', help='讀取一個檔案的內容並輸出到 stdout。')
    # 告訴「read」子翻譯官，它需要一個名叫「path」的「參數（argument）」。
    parser_read.add_argument('path', help='要讀取的檔案路徑。')
    
    # 4. 定義「write」這個「子翻譯官」。
    parser_write = subparsers.add_parser('write', help='從標準輸入讀取內容，並將其寫入一個檔案。')
    parser_write.add_argument('path', help='要寫入的檔案路徑。')

    # 5. 定義「validate」這個「子翻譯官」。
    parser_validate = subparsers.add_parser('validate', help='驗證一個或多個路徑是否存在。')
    # 「nargs='+'」的意思是，這個「paths」參數可以接收一個或多個值。
    parser_validate.add_argument('paths', nargs='+', help='要驗證的路徑列表。')

        # 【新】定義「normalize」這個「子翻譯官」。
    parser_normalize = subparsers.add_parser('normalize', help='將一個路徑字串標準化為 Linux 格式並輸出。')
    parser_normalize.add_argument('path', help='要標準化的路徑字串。')


    # 6. 命令「總翻譯官」開始解析（parse）實際傳入的「指令（args）」。
    args = parser.parse_args()

    # 7. 我們用「if...elif...」結構，來根據解析出的「命令（command）」去執行對應的動作。
    if args.command == 'read':
        # 在執行任何動作前，我們先調用「normalize_path」函式，把路徑「標準化」。
        normalized_filepath = normalize_path(args.path)
        # 然後把標準化後的路徑，交給「handle_read」函式去處理。
        handle_read(normalized_filepath)
    elif args.command == 'write':
        normalized_filepath = normalize_path(args.path)
        # 因為 handle_write 現在從標準輸入讀取，所以不再需要傳遞第二個參數
        handle_write(normalized_filepath) 
    elif args.command == 'validate':
        # 我們用一個「列表推導式」，來一次性把所有傳入的路徑都進行標準化。
        normalized_paths = [normalize_path(p) for p in args.paths]
        handle_validate(normalized_paths)
    elif args.command == 'normalize':
        # 直接調用 normalize_path 函式，並打印結果到標準輸出
        print(normalize_path(args.path))
        sys.exit(0)


# 這是一個 Python 的慣例：
# 只有當這個腳本是被「直接執行（python3 path.py ...）」而不是被「導入（import path）」時，
# 「__name__」這個特殊變數的值才會是「"__main__"」。
if __name__ == "__main__":
    # 我們在這裡呼叫「main」主函式，讓整個程式跑起來。
    main()
