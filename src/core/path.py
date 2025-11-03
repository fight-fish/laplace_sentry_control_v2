# src/core/path.py

# 我們需要導入（import）幾個 Python 內建的標準工具：
import os       # 用於與「作業系統（os）」互動，如檢查路徑。
import sys      # 用於讀取「系統（sys）」參數和控制腳本退出。
import argparse # 用於創建專業的「命令列參數（argparse）」介面。
import re       # 用於執行強大的「正規表達式（re）」匹配。

# --- 核心路徑處理函式 (Core Path Processing Functions) ---

def normalize_path(path_str):
    """
    【v2.4 穩定版】
    將各種平台、各種格式的原始路徑字串，標準化為統一的、在 WSL 中可用的 Linux 路徑格式。
    這是我們在日誌 035 中，通過血淚教訓換來的、能處理真實世界「髒數據」的函式。
    """
    # DEFENSE: 如果傳入的不是一個字串，直接返回空字串，防止後續操作出錯。
    if not isinstance(path_str, str):
        return ""

    # 我們先用 strip() 去掉路徑頭尾可能存在的空白字符。
    p = path_str.strip()

    # HACK: 處理從 Windows 檔案總管複製出來、被多層引號包裹的路徑。
    # 我們用一個「while」循環，來不斷地「剝洋蔥」，直到最外層不再是引號。
    while p.startswith(('"', "'")) and p.endswith(('"', "'")):
        p = p[1:-1].strip()

    # 我們用 replace() 將所有 Windows 風格的反斜線（\）替換為 Linux 風格的正斜線（/）。
    p = p.replace("\\", "/")

    # HACK: 處理來自 WSL 的 UNC 路徑，例如 `//wsl.localhost/Ubuntu/home/user`。
    # 這裡的正規表達式 `^/{1,2}wsl\.localhost/([^/]+)/(.*)` 是我們除錯的關鍵成果。
    # 它能同時匹配 `//wsl.localhost` 和 `/wsl.localhost` 兩種情況。
    match_wsl = re.match(r"^/{1,2}wsl\.localhost/([^/]+)/(.*)", p, re.IGNORECASE)
    if match_wsl:
        # 如果匹配成功，我們就丟掉前面的主機名，只保留後面的真實路徑部分。
        p = "/" + match_wsl.group(2)

    # HACK: 處理 Windows 的磁碟機代號路徑，例如 `D:/Obsidian_Vaults/...`。
    match_drive = re.match(r"([A-Za-z]):/(.*)", p)
    if match_drive:
        drive_letter = match_drive.group(1).lower()
        rest_of_path = match_drive.group(2)
        # 我們將其轉換為 WSL 中對應的掛載路徑格式。
        p = f"/mnt/{drive_letter}/{rest_of_path}"

    # 最後，我們用 re.sub() 將路徑中可能出現的多個連續斜線（如 `//`）壓縮為單個斜線。
    p = re.sub(r"/{2,}", "/", p)
    return p

def validate_paths_exist(paths_to_check):
    """
    一個可被其他 Python 模組導入的工具函式，用於檢查一個路徑列表是否都真實存在。
    返回 True (全部存在) 或 False (至少一個不存在)。
    """
    # 我們用「for...in...」這個結構，來一個一個地遍歷傳入的「路徑列表（paths_to_check）」。
    for path in paths_to_check:
        # 我們用「os.path.exists()」來判斷，如果（if not）這個路徑「不存在（exists）」...
        if not os.path.exists(path):
            # ...就立刻返回（return）一個代表「失敗」的布林值 False，終止檢查。
            return False
    # 如果循環順利跑完（代表所有路徑都存在），就返回（return）一個代表「成功」的布林值 True。
    return True

# --- 核心命令處理函式 (Command Handler Functions) ---

def handle_read(filepath):
    """處理 'read' 命令的邏輯。"""
    # DEFENSE: 我們用「if not os.path.isfile()」來判斷，如果這個路徑不是一個存在的「檔案（file）」...
    if not os.path.isfile(filepath):
        # ...我們就向「標準錯誤流（sys.stderr）」打印一條錯誤訊息。
        print(f"【路徑專家錯誤】：要讀取的檔案不存在！\n  -> {filepath}", file=sys.stderr)
        # 然後用「sys.exit(2)」，帶著一個代表「路徑錯誤」的退出碼「2」，立刻「退出（exit）」腳本。
        sys.exit(2)
    # DEFENSE: 我們用「try...except...」結構，來捕獲讀取文件時可能發生的任何意外。
    try:
        # 「with open(...)」是一個安全的讀取檔案方式，它能確保檔案在結束後被自動關閉。
        with open(filepath, 'r', encoding='utf-8') as f:
            # 我們只做一件事：讀取檔案的「全部內容（content）」，然後「打印（print）」到標準輸出。
            print(f.read())
        # 如果一切順利，就用「sys.exit(0)」，帶著代表「成功」的退出碼「0」，退出腳本。
        sys.exit(0)
    except Exception as e:
        print(f"【路徑專家錯誤】：讀取檔案 '{filepath}' 時發生未知錯誤！\n  -> {e}", file=sys.stderr)
        # 如果發生異常，就帶著退出碼「3」（代表其他內部錯誤）退出。
        sys.exit(3)

def handle_write(filepath):
    """處理 'write' 命令的邏輯，從標準輸入讀取內容。"""
    # 我們先獲取目標檔案所在的目錄路徑。
    parent_dir = os.path.dirname(filepath)
    # DEFENSE: 如果父目錄存在且不是一個有效的目錄...
    if parent_dir and not os.path.isdir(parent_dir):
        print(f"【路徑專家錯誤】：要寫入的目標檔案所在的資料夾不存在！\n  -> {parent_dir}", file=sys.stderr)
        sys.exit(2)
    try:
        # 我們從「標準輸入（sys.stdin）」讀取所有通過管道傳來的內容。
        content_to_write = sys.stdin.read()
        # 以「寫入模式（'w'）」打開檔案，並將內容寫入。
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_to_write)
        sys.exit(0)
    except Exception as e:
        print(f"【路徑專家錯誤】：寫入檔案 '{filepath}' 時發生未知錯誤！\n  -> {e}", file=sys.stderr)
        sys.exit(3)

def handle_validate(paths):
    """處理 'validate' 命令的邏輯。"""
    # 這個為命令列服務的函式，現在去調用我們前面定義的工具函式。
    if not validate_paths_exist(paths):
        # 如果（if not）工具函式返回了 False，我們就在這裡打印統一的錯誤訊息。
        print(f"【路徑專家錯誤】：一個或多個路徑不存在或無效。", file=sys.stderr)
        sys.exit(2)
    # 如果返回 True，我們就什麼都不打印，並帶著退出碼「0」（代表成功）安靜地退出。
    sys.exit(0)

# --- 主執行區：命令列介面設定 (Main Execution: CLI Setup) ---

def main():
    """定義並執行程式的命令列介面。"""
    # 1. 我們創建一個「總翻譯官（parser）」。
    parser = argparse.ArgumentParser(
        description="路徑與 I/O 專家：負責所有檔案的讀、寫、驗證、標準化操作。",
        formatter_class=argparse.RawTextHelpFormatter # 這個選項能讓幫助訊息保持我們寫的格式。
    )
    # 2. 我們告訴「總翻譯官」，它下面可以有多個「子命令（subparsers）」。
    subparsers = parser.add_subparsers(dest='command', required=True, help='可執行的子命令')

    # 3. 定義「read」子命令。
    parser_read = subparsers.add_parser('read', help='讀取一個檔案的內容並輸出到 stdout。')
    parser_read.add_argument('path', help='要讀取的檔案路徑。')

    # 4. 定義「write」子命令。
    parser_write = subparsers.add_parser('write', help='從標準輸入讀取內容，並將其寫入一個檔案。')
    parser_write.add_argument('path', help='要寫入的檔案路徑。')

    # 5. 定義「validate」子命令。
    parser_validate = subparsers.add_parser('validate', help='驗證一個或多個路徑是否存在。')
    # 「nargs='+'」的意思是，這個「paths」參數可以接收一個或多個值。
    parser_validate.add_argument('paths', nargs='+', help='要驗證的路徑列表。')

    # 6. 定義「normalize」子命令。
    parser_normalize = subparsers.add_parser('normalize', help='將一個路徑字串標準化為 Linux 格式並輸出。')
    parser_normalize.add_argument('path', help='要標準化的路徑字串。')

    # 7. 命令「總翻譯官」開始解析（parse）實際傳入的「指令（args）」。
    args = parser.parse_args()

    # 8. 我們用「if...elif...」結構，來根據解析出的「命令（command）」去執行對應的處理函式。
    if args.command == 'read':
        # 在執行任何動作前，我們先調用「normalize_path」函式，把路徑「標準化」。
        normalized_filepath = normalize_path(args.path)
        handle_read(normalized_filepath)
    elif args.command == 'write':
        normalized_filepath = normalize_path(args.path)
        handle_write(normalized_filepath)
    elif args.command == 'validate':
        # 我們用一個「列表推導式」，來一次性把所有傳入的路徑都進行標準化。
        normalized_paths = [normalize_path(p) for p in args.paths]
        handle_validate(normalized_paths)
    elif args.command == 'normalize':
        # 直接調用 normalize_path 函式，並將結果打印到標準輸出。
        print(normalize_path(args.path))
        sys.exit(0)

# 這是一個 Python 的標準寫法。
# 它確保只有當這個文件被直接執行時（而不是被當作模組導入時），main() 函式才會被調用。
if __name__ == "__main__":
    main()
