# ==============================================================================
# 模組職責：path.py
# - 提供跨平台安全的路徑正規化（normalize_path）
# - 提供基礎路徑存在性驗證（validate_paths_exist）
# - 暴露簡單 CLI：read / write / validate / normalize / atomic_write
#
# 已知風險與歷史：
# - atomic_write 現在由 io_gateway 接手，僅作為 CLI 兼容保留（見 COMPAT）
# - 路徑正規化特別處理 WSL UNC 與 Windows 磁碟機路徑
# ==============================================================================


# 我們需要 導入（import）一系列 Python 內建的工具，來幫助我們與作業系統和命令行互動。
import os       # 用於與「作業系統（os）」互動，如檢查路徑。
import sys      # 用於讀取「系統（sys）」參數和控制腳本退出。
import argparse # 用於創建專業的「指令翻譯官（argparse）」。
import re       # 用於執行強大的「正規表達式（re）」匹配。
import tempfile # 用於創建「臨時文件（tempfile）」。
import portalocker # 用於實現跨進程的「文件鎖（portalocker）」。
import time     # 用於處理「時間（time）」相關操作。

# --- 核心路徑處理函式 ---

# 我們用「def」來 定義（define）一個函式，名叫「normalize_path」。
# 它的作用是將各種亂七八糟的路徑，都「正規化」成我們系統內部統一的、乾淨的格式。
def normalize_path(path_str):
    
    # DEFENSE:
    # 為了防止後續操作因為接收到非字串而出錯，我們先做一個防禦性檢查。
    # 我們用「isinstance」來判斷，如果（if not）傳入的「path_str」不是一個「字串（str）」...
    if not isinstance(path_str, str):
        # ...我們就直接 返回（return）一個空字串。
        return ""

    # 我們先用「strip()」方法，去掉路徑頭尾可能存在的空白字符。
    p = path_str.strip()

    # HACK:
    # 這是為了處理一個真實世界的「髒數據」問題：從 Windows 檔案總管複製的路徑，
    # 常常會被多層引號（如 "'...'"）包裹。
    # 我們用一個「while」循環，來不斷地「剝洋蔥」，直到最外層不再是引號。
    while p.startswith(('"', "'")) and p.endswith(('"', "'")):
        p = p[1:-1].strip()

    # TAG: PORT (可移植性)
    # 我們用「replace()」方法，將所有 Windows 風格的反斜線（\），都替換為 Linux 風格的正斜線（/）。
    # 這確保了我們的路徑處理邏輯在跨平台時的兼容性。
    p = p.replace("\\", "/")

    # HACK:
    # 這是為了處理另一個真實世界的「髒數據」問題：來自 WSL 的 UNC 路徑。
    # 例如 `//wsl.localhost/Ubuntu/home/user`。
    # 我們用「re.match」和一段複雜的正規表達式，來精準地匹配這種特殊格式。
    match_wsl = re.match(r"^/{1,2}wsl\.localhost/([^/]+)/(.*)", p, re.IGNORECASE)
    # 如果（if）匹配成功...
    if match_wsl:
        # ...我們就丟掉前面的主機名，只保留後面的真實路徑部分。
        p = "/" + match_wsl.group(2)

    # HACK:
    # 這是為了處理 Windows 的磁碟機代號路徑，例如 `D:/Obsidian_Vaults/...`。
    match_drive = re.match(r"([A-Za-z]):/(.*)", p)
    if match_drive:
        # 我們將其轉換為 WSL 中對應的掛載路徑格式，例如 `/mnt/d/Obsidian_Vaults/...`。
        drive_letter = match_drive.group(1).lower()
        rest_of_path = match_drive.group(2)
        p = f"/mnt/{drive_letter}/{rest_of_path}"

    # 最後，我們用「re.sub()」將路徑中可能出現的多個連續斜線（如 `//`）壓縮為單個斜線。
    p = re.sub(r"/{2,}", "/", p)
    return p

# 我們用「def」來 定義（define）一個函式，名叫「validate_paths_exist」。
# 它的作用是檢查一個「路徑籃子（[]）」裡的所有路徑，是否都真實存在。
def validate_paths_exist(paths_to_check):
    # 我們用「for...in...」這個結構，來一個一個地處理「paths_to_check」籃子裡的路徑。
    for path in paths_to_check:
        # 我們用「os.path.exists()」來判斷，如果（if not）這個路徑「不存在（exists）」...
        if not os.path.exists(path):
            # ...就立刻 返回（return）一個代表「失敗」的布林值 False，終止檢查。
            return False
    # 如果循環順利跑完（代表所有路徑都存在），就 返回（return）一個代表「成功」的布林值 True。
    return True

# --- 核心命令處理函式 ---

# 處理「read」命令的邏輯。
def handle_read(filepath):
    # DEFENSE:
    # 我們用「os.path.isfile()」來判斷，如果（if not）這個路徑不是一個存在的「檔案（file）」...
    if not os.path.isfile(filepath):
        # ...我們就向「標準錯誤流（sys.stderr）」打印一條錯誤訊息。
        print(f"【路徑專家錯誤】：要讀取的檔案不存在！\n  -> {filepath}", file=sys.stderr)
        # 然後用「sys.exit(2)」，帶著一個代表「資源不存在」的退出碼「2」，立刻「退出（exit）」腳本。
        sys.exit(2)
    
    # DEFENSE:
    # 我們用「try...except...」結構，來捕獲讀取文件時可能發生的任何意外。
    try:
        # 「with open(...)」是一個安全的讀取檔案方式，它能確保檔案在結束後被自動關閉。
        with open(filepath, 'r', encoding='utf-8') as f:
            # 我們只做一件事：讀取檔案的「全部內容（content）」，然後「打印（print）」到標準輸出。
            print(f.read())
        # 如果一切順利，就用「sys.exit(0)」，帶著代表「成功」的退出碼「0」，退出腳本。
        sys.exit(0)
    except Exception as e:
        print(f"【路徑專家錯誤】：讀取檔案 '{filepath}' 時發生未知錯誤！\n  -> {e}", file=sys.stderr)
        # 如果發生異常，就帶著退出碼「9」（代表系統級錯誤）退出。
        sys.exit(9)

# 處理「write」命令的邏輯。
def handle_write(filepath):
    # 我們先獲取目標檔案所在的目錄路徑。
    parent_dir = os.path.dirname(filepath)
    # DEFENSE:
    # 如果父目錄存在，但它不是一個有效的目錄...
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
        sys.exit(9)

# 處理「validate」命令的邏輯。
def handle_validate(paths):
    # 這個為命令列服務的函式，現在去調用我們前面定義的工具函式。
    if not validate_paths_exist(paths):
        # 如果（if not）工具函式返回了 False，我們就在這裡打印統一的錯誤訊息。
        print(f"【路徑專家錯誤】：一個或多個路徑不存在或無效。", file=sys.stderr)
        sys.exit(2)
    # 如果返回 True，我們就什麼都不打印，並帶著退出碼「0」（代表成功）安靜地退出。
    sys.exit(0)

# 處理「atomic_write」命令的邏輯。
def handle_atomic_write(filepath):
    # 【注意】此函式已在「I/O 網關」重構後，被 `io_gateway.py` 取代。
    # 它目前在我們的核心流程中已不再被使用，僅作為一個可獨立運行的命令行工具保留。
    
    # 我們根據傳入的目標文件，動態生成一個伴生的「鎖文件」路徑。
    lock_path = filepath + ".lock"
    
    parent_dir = os.path.dirname(filepath)
    if parent_dir and not os.path.isdir(parent_dir):
        print(f"【路徑專家錯誤】：要寫入的目標檔案所在的資料夾不存在！\n  -> {parent_dir}", file=sys.stderr)
        sys.exit(2)
    
    content_to_write = sys.stdin.read()

    try:
        # 我們用「with portalocker.Lock(...)」結構，來嘗試獲取那個伴生鎖。
        # 「timeout=5」表示如果 5 秒內搶不到鎖，就放棄並報錯。
        with portalocker.Lock(lock_path, 'w', timeout=5) as fh:
            # --- 獲取鎖之後的邏輯，與我們在 io_gateway.py 中的設計類似 ---
            # 我們用「with tempfile.NamedTemporaryFile(...)」來創建一個安全的臨時文件。
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, dir=parent_dir) as tmp:
                temp_path = tmp.name
                tmp.write(content_to_write)
                tmp.flush()
                os.fsync(tmp.fileno())
            
            # 這是原子操作的關鍵一步：用新寫好的臨時文件，去「替換」原始的目標文件。
            os.replace(temp_path, filepath)

    except portalocker.LockException as e:
        print(f"【路徑專家錯誤】：無法獲取文件鎖，可能正被另一進程佔用。\n  -> 鎖文件: {lock_path}\n  -> 原因: {e}", file=sys.stderr)
        sys.exit(9)
    except Exception as e:
        print(f"【路徑專家錯誤】：執行原子寫入到 '{filepath}' 時發生未知錯誤！\n  -> {e}", file=sys.stderr)
        # 如果在過程中發生任何錯誤，我們嘗試清理可能遺留的臨時文件。
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        sys.exit(9)
    
    sys.exit(0)


# --- 主執行區：命令列介面設定 ---

# 我們用「def」來 定義（define）一個我們這個腳本最主要的函式，名叫「main」。
def main():
    # 我們創建一個「總翻譯官（parser）」。
    parser = argparse.ArgumentParser(
        description="路徑與 I/O 專家：負責所有檔案的讀、寫、驗證、標準化操作。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # 我們告訴「總翻譯官」，它下面可以有多個「子命令（subparsers）」。
    subparsers = parser.add_subparsers(dest='command', required=True, help='可執行的子命令')

    # 定義「read」子命令。
    parser_read = subparsers.add_parser('read', help='讀取一個檔案的內容並輸出到 stdout。')
    parser_read.add_argument('path', help='要讀取的檔案路徑。')

    # 定義「write」子命令。
    parser_write = subparsers.add_parser('write', help='從標準輸入讀取內容，並將其寫入一個檔案。')
    parser_write.add_argument('path', help='要寫入的檔案路徑。')

    # 定義「validate」子命令。
    parser_validate = subparsers.add_parser('validate', help='驗證一個或多個路徑是否存在。')
    # 「nargs='+'」的意思是，這個「paths」參數可以接收一個或多個值。
    parser_validate.add_argument('paths', nargs='+', help='要驗證的路徑列表。')

    # 定義「normalize」子命令。
    parser_normalize = subparsers.add_parser('normalize', help='將一個路徑字串標準化為 Linux 格式並輸出。')
    parser_normalize.add_argument('path', help='要標準化的路徑字串。')

    # 定義「atomic_write」子命令。
    parser_atomic_write = subparsers.add_parser('atomic_write', help='以安全、原子的方式寫入文件。')
    parser_atomic_write.add_argument('path', help='要寫入的檔案路徑。')

    # 命令「總翻譯官」開始解析（parse）實際傳入的「指令（args）」。
    args = parser.parse_args()

    # 我們用「if...elif...」結構，來根據解析出的「命令（command）」去執行對應的處理函式。
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
    elif args.command == 'atomic_write':
        normalized_filepath = normalize_path(args.path)
        handle_atomic_write(normalized_filepath)

# 這是一個 Python 的標準寫法。
# 它確保只有當這個文件被直接執行時，main() 函式才會被調用。
if __name__ == "__main__":
    main()
