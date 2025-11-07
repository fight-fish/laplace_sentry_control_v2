# src/core/io_gateway.py

# 我們需要 導入（import）一系列 Python 內建的工具。
import os          # 用於與「作業系統（os）」互動。
import json        # 用於處理「JSON」格式的數據。
import portalocker # 我們最核心的「文件鎖（portalocker）」工具。
from typing import Callable, Any # 用於提供更精確的「類型提示（typing）」。

# 我們用「def」來 定義（define）一個我們這個腳本最核心的函式，名叫「safe_read_modify_write」。
# 它的作用是提供一個絕對安全的「讀取-修改-寫入」事務。
def safe_read_modify_write(
    file_path: str,
    update_callback: Callable[[Any], Any],
    serializer: str = 'json'
) -> Any:
    
    # 我們直接鎖定目標文件本身。因為我們不再使用 os.replace，所以這個文件不會在操作中消失。
    lock_path = file_path

    # TAG: DEFENSE
    # 我們用一個巨大的「try...except...」結構，來捕獲在整個 I/O 過程中可能發生的所有已知和未知的錯誤。
    # 這確保了我們的 I/O 網關本身是極其健壯的，不會輕易崩潰。
    try:
        # 我們以「r+」（讀寫模式）來 打開（open）文件。
        # 這意味著我們期望這個文件已經存在。
        with open(lock_path, 'r+', encoding='utf-8') as f:
            # 在打開文件後，我們立刻對這個文件句柄「f」上鎖（lock）。
            # 「LOCK_EX」代表這是一個「排他鎖」，在我們釋放它之前，不允許任何其他進程操作這個文件。
            portalocker.lock(f, portalocker.LOCK_EX)
            
            # --- 從這裡開始，我們進入了絕對安全的「鎖定區域」---

            # 1. 讀取數據
            # 我們先 讀取（read）文件的全部內容。
            content = f.read()
            # 我們準備一個「current_data」變數，用來存放解析後的數據。
            current_data = [] if serializer == 'json' else ""
            # 如果（if）文件內容不是空的...
            if content:
                try:
                    # ...並且（if）序列化器是「json」...
                    if serializer == 'json':
                        # ...我們就用「json.loads」來解析它。
                        current_data = json.loads(content)
                    else:
                        # 否則，就直接把原始文本內容賦值過去。
                        current_data = content
                except json.JSONDecodeError:
                    # TAG: DEFENSE
                    # 如果在解析 JSON 時出錯（比如文件損壞），我們不能讓程式崩潰。
                    # 我們選擇「pass」，也就是靜默地跳過這個錯誤，讓「current_data」保持為一個安全的空列表。
                    pass

            # 2. 調用回調函式，執行「修改」邏輯
            # 這是這個網關最核心的設計：它將「如何修改數據」的權力，交還給了調用者。
            # 我們執行調用者傳入的「update_callback」函式，並把當前數據傳給它。
            new_data = update_callback(current_data)

            # 3. 準備寫入的內容
            content_to_write = ""
            if serializer == 'json':
                # 我們用「json.dumps」將修改後的新數據，轉換回 JSON 格式的字串。
                content_to_write = json.dumps(new_data, indent=2, ensure_ascii=False)
            else:
                content_to_write = str(new_data)

            # 4. 寫入新內容
            # 我們用「seek(0)」將文件的讀寫指針，移回文件的最開頭。
            f.seek(0)
            # 我們用「truncate()」將文件從當前位置截斷，也就是清空文件的所有舊內容。
            f.truncate()
            # 我們用「write()」將全新的內容，寫入這個已被清空的文件。
            f.write(content_to_write)
            
            # 在主邏輯成功結束時，明確地 返回（return）修改後的新數據。
            return new_data

    # 我們用「except FileNotFoundError」來捕獲一種特殊情況：如果文件一開始就不存在。
    except FileNotFoundError:
        # 在這種情況下，我們嘗試以「w」（寫入模式）來創建它。
        try:
            with open(lock_path, 'w', encoding='utf-8') as f:
                # 同樣，創建後立刻上鎖。
                portalocker.lock(f, portalocker.LOCK_EX)
                # 我們假設初始數據是一個空的「籃子」或空字串。
                initial_data = [] if serializer == 'json' else ""
                # 同樣執行回調函式。
                new_data = update_callback(initial_data)
                # 準備要寫入的內容。
                content_to_write = ""
                if serializer == 'json':
                    content_to_write = json.dumps(new_data, indent=2, ensure_ascii=False)
                else:
                    content_to_write = str(new_data)
                # 將內容寫入這個新創建的文件。
                f.write(content_to_write)
                
                # 在創建新文件成功時，也明確地 返回（return）新數據。
                return new_data
        except Exception as e:
            # 如果在創建過程中也失敗了，我們就拋出一個「IOError」異常。
            raise IOError(f"創建並寫入新文件時出錯: {e}")

    # 如果是因為「無法獲取鎖」而失敗...
    except portalocker.LockException:
        # 我們就拋出一個帶有清晰說明的「IOError」異常。
        raise IOError(f"無法獲取文件鎖，目標 '{os.path.basename(file_path)}' 可能正被另一進程操作。")
    # 如果是其他所有未預料到的錯誤...
    except Exception as e:
        # 我們也將其包裝成一個「IOError」異常拋出，並附上原始錯誤信息。
        raise IOError(f"執行安全讀寫事務時發生未知錯誤: {e}")
