# 我們需要 導入 (import) 一個叫「re」的工具，它非常擅長用「正規表達式」來尋找和替換文字。
import re
# 我們需要 導入 (import) 一個叫「sys」的工具，它能幫助我們讀取從外部傳來的指令，方便我們進行獨立測試。
import sys

# 我們用「def」來 定義 (define) 一個名叫「normalize_path」的函式。
# 這就是我們「尋路專家」的核心大腦。
def normalize_path(path_str):
    """
    將各種平台、各種格式的原始路徑字串，標準化為統一的、在 WSL 中可用的 Linux 路徑格式。
    """
    # 我們準備一個臨時變數「p」，用來對傳入的路徑（path_str）進行一步步的處理。
    p = path_str

    # --- 第 1 步：脫掉頭尾可能存在的引號和空白 ---
    # 我們用「strip」這個方法，一次性地把頭尾的「'」、「"」和空白字元都去掉。
    p = p.strip().strip("'\"")

    # --- 第 2 步：將所有反斜線「\」替換為正斜線「/」 ---
    # 我們用「replace」這個方法，把所有的「\\」都換成「/」。
    p = p.replace("\\", "/")

    # --- 第 3 步：處理 WSL 網路路徑 (如 \\wsl.localhost\Ubuntu\home...) ---
    # 我們用「re.search」來尋找，路徑中是否包含「wsl.localhost/」這種模式。
    # 「re.IGNORECASE」表示我們不在乎大小寫。
    match_wsl = re.search(r"//wsl\.localhost/[^/]+/(.*)", p, re.IGNORECASE)
    if match_wsl:
        # 如果找到了，我們就只取「(.*)」這部分匹配到的內容，並在前面加上「/」。
        p = "/" + match_wsl.group(1)

    # --- 第 4 步：處理 Windows 磁碟機代號路徑 (如 D:/... 或 C:\...) ---
    # 我們用「re.match」來判斷，路徑是否是以「一個字母 + : /」開頭的。
    match_drive = re.match(r"([A-Za-z]):/(.*)", p)
    if match_drive:
        # 如果匹配上了，我們就取出「磁碟機代號」和「後面的路徑」。
        drive_letter = match_drive.group(1).lower()
        rest_of_path = match_drive.group(2)
        # 然後，我們把它們組合成「/mnt/磁碟機代號/後面的路徑」的格式。
        p = f"/mnt/{drive_letter}/{rest_of_path}"

    # --- 第 5 步：清理多餘的斜線 ---
    # 我們用「re.sub」來把兩個或更多連續的斜線（如「//」或「///」），替換成一個。
    p = re.sub(r"/{2,}", "/", p)

    # 最後，我們把這條經過千錘百鍊、煥然一新的路徑，「返回（return）」給呼叫者。
    return p

# 這是我們為「尋路專家」準備的獨立測試區。
# 只有當這個腳本被「直接執行」時，才去運行下面的程式碼。
if __name__ == "__main__":
    # 我們判斷（if）從外部收到的「參數個數」是不是剛好 2 個。
    if len(sys.argv) != 2:
        print("用法: python3 path_engine.py \"<要測試的路徑>\"")
        # 我們用「sys.exit(1)」來立即終止程式，並告訴系統這是一次因錯誤而導致的退出。
        sys.exit(1)
    
    # 我們把收到的第 2 個參數，作為「原始路徑」。
    original_path = sys.argv[1]
    # 我們呼叫我們的核心函式，來處理這個原始路徑。
    normalized = normalize_path(original_path)

    # 我們把處理前後的結果都打印出來，方便對比。
    print("--- 尋路專家獨立測試 ---")
    print(f"原始路徑: {original_path}")
    print(f"標準化後: {normalized}")

