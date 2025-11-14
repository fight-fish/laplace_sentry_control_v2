# 我們需要 導入（import）一些基本的工具。
import sys
import time
import os
import signal
from typing import Dict
# 我們從 watchdog 這個第三方庫中，導入我們需要的兩個核心組件。
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
# 【TECH-DEBT-STATELESS-SENTRY 核心改造】
# 理由：我們不希望哨兵工人在主控台被 Ctrl+C 關閉時，也跟著「殉職」。
# 我們希望它能頑強地活下來，等待下一次主控台重啟時，被「狀態恢復」系統重新納管。
# signal.SIG_IGN 是一個特殊的處理器，它告訴操作系統：「忽略這個信號，假裝什麼都沒發生。」
signal.signal(signal.SIGINT, signal.SIG_IGN)
# --- 【v5.0 核心改造】 ---
# 我們在程式碼的頂部，定義一個名為「SENTRY_INTERNAL_IGNORE」的「絕對禁區」列表。
# 這是一個元組（tuple），意味著它的內容是不可修改的，更加安全。
# 我們將所有系統自身會產生變動的目錄，都放入這個禁區。
SENTRY_INTERNAL_IGNORE = ('logs', 'temp', 'data','.git', '__pycache__', '.venv', '.vscode')

# --- 【v5.4 抖動抑制器】 ---
# 我們用「class」關鍵字，來定義一個全新的類，名叫「EventThrottler」。
class EventThrottler:
    # 我們用「def __init__」來定義這個類的「初始化方法」。
    # 當我們創建一個 EventThrottler 的實例時，這個方法會被自動調用。
    def __init__(self, delay: float = 2.0):
        # 「delay」是我們的「冷靜期」，單位是秒。
        self.delay = delay
        # 「self.timestamps」是一個字典，用來記錄我們為每個文件「關上門」的時間點。
        # Key 是文件路徑，Value 是時間戳。
        self.timestamps: Dict[str, float] = {}

    # 我們定義一個方法，名叫「should_process」。
    # 它的作用是判斷：對於傳入的這個「事件（event）」，我們是否應該處理它？
    def should_process(self, event) -> bool:
        # 我們只對「文件被修改（modified）」和「文件被創建（created）」的事件進行抖動抑制。
        # 對於「刪除」或「移動」等事件，我們總是立即處理。
        if event.event_type not in ('modified', 'created'):
            return True

        # 我們獲取事件發生的文件路徑。
        path = event.src_path
        # 我們獲取當前的時間戳。
        now = time.time()
        
        # 我們從「時間戳字典」中，獲取該文件上一次被處理的時間。
        # .get(path, 0) 的意思是，如果找不到這個文件，就默認返回 0。
        last_processed_time = self.timestamps.get(path, 0)

        # 核心判斷：如果（if）「現在」距離「上次處理的時間」大於我們的「冷靜期」...
        if now - last_processed_time > self.delay:
            # ...這意味著冷靜期已過，這是一個全新的、需要被處理的事件。
            # 我們更新「時間戳字典」，將當前時間記錄為這個文件的「最新處理時間」。
            self.timestamps[path] = now
            # 然後 返回（return）True，表示「應該處理」。
            return True
        
        # 否則（else），如果還在冷靜期內...
        # 我們就 返回（return）False，表示「應該忽略」。
        return False

# ... import 語句 ...
# HACK: 為了能導入 src/core 下的模塊，我們臨時將專案根目錄添加到系統路徑中。
project_root_for_import = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root_for_import not in sys.path:
    sys.path.insert(0, project_root_for_import)

from src.core import daemon # <--- 新增：導入我們的指揮官

# 我們用「class」關鍵字，來定義一個我們自己的「事件處理器」。
class SentryEventHandler(FileSystemEventHandler):
        # 在處理器的初始化方法中，我們創建一個「抖動抑制器」的實例。
    def __init__(self, throttler: EventThrottler, project_uuid: str):
        self.throttler = throttler
        self.project_uuid = project_uuid
    # 我們用「def」來 定義（define）一個方法，名叫「on_any_event」。
    def on_any_event(self, event):
        
        # --- 【v5.2 最終過濾版】 ---
        # 我們首先確保我們處理的是一個字串路徑。
        if isinstance(event.src_path, str):
            # 我們將事件路徑，通過 os.path.normpath 進行標準化，消除多餘的斜線。
            normalized_path = os.path.normpath(event.src_path)
            # 我們用 split(os.sep) 將路徑分割成一個個的部分，例如 ['home', 'serpal', 'project', 'data', 'file.json']
            path_parts = normalized_path.split(os.sep)

            # 我們用 any() 和一個生成器表達式，來判斷路徑的任何一個部分，是否存在於我們的禁區列表中。
            # 這比手動拼接字串要健壯得多。
            if any(part in SENTRY_INTERNAL_IGNORE for part in path_parts):
                return

                    # --- 【v5.4 核心改造】 ---
        # 在打印任何日誌之前，我們先詢問「抖動抑制器」，這個事件是否應該被處理。
        # 我們用「if not」來判斷，如果（if not）不應該處理...
        if not self.throttler.should_process(event):
            # ...我們就直接「返回（return）」，將其靜默過濾掉。
            return
        # 只有通過了上面所有嚴格檢查的事件，才能到達這裡。
        print(f"[{time.strftime('%H:%M:%S')}] [安全事件] 偵測到: {event.event_type} - 路徑: {event.src_path}")
        sys.stdout.flush()

        # --- 【v5.0 核心集成邏輯】 ---
        try:
            # 1. 我們從指揮官那裡獲取完整的專案列表。
            all_projects = daemon.handle_list_projects()
            # 2. 我們在列表中，查找與自己 UUID 匹配的那個專案。
            project_config = next((p for p in all_projects if p.get('uuid') == self.project_uuid), None)

            if not project_config:
                print(f"【哨兵錯誤】: 在 projects.json 中找不到 UUID 為 {self.project_uuid} 的專案配置。", file=sys.stderr)
                return

            # 3. 我們從配置中，解析出執行任務所需的所有情報。
            project_path = project_config.get('path')
            targets = daemon._get_targets_from_project(project_config) # 複用 daemon 的輔助函式
            target_doc = targets[0] if targets else None
            ignore_list = project_config.get("ignore_patterns")
            ignore_patterns = set(ignore_list) if isinstance(ignore_list, list) else None

            if not project_path or not target_doc:
                print(f"【哨兵錯誤】: 專案 '{project_config.get('name')}' 缺少有效的路徑配置。", file=sys.stderr)
                return

            # 4. 我們直接調用指揮官的 handle_manual_direct 函式，下達更新指令！
            print(f"[{time.strftime('%H:%M:%S')}] [哨兵情報] 目標: {os.path.basename(target_doc)}, 忽略規則: {ignore_patterns}")
            daemon.handle_manual_direct([project_path, target_doc], ignore_patterns=ignore_patterns)
            
            print(f"[{time.strftime('%H:%M:%S')}] [哨兵行動] 更新流程已成功觸發。")

        except Exception as e:
            # 任何在上述流程中發生的意外，都會被這個安全網捕獲。
            print(f"【哨兵致命錯誤】: 在執行更新流程時發生意外: {e}", file=sys.stderr)
        finally:
            sys.stdout.flush()

# 我們用「def」來 定義（define）這個工人的主函式。
def main():
    # --- 【v5.5 參數化改造】 ---
    # 1. 我們檢查從命令行傳入的參數（sys.argv）數量。
    #    列表的第一個元素是腳本名本身，所以我們期望總長度是 2。
    if len(sys.argv) != 3:
        # 如果參數數量不對，我們就在「標準錯誤流」中打印用法，並以失敗碼退出。
        print("用法: python sentry_worker.py <project_uuid> <project_path>", file=sys.stderr)
        sys.exit(1)

    # 2. 如果參數數量正確，我們就從列表中取出第二個元素，這就是我們需要的 UUID。
    project_uuid = sys.argv[1]
    project_path_to_watch = sys.argv[2]

        # 3. 我們在啟動日誌中，加入我們剛剛獲取的 project_uuid，以便驗證。
    print(f"哨兵工人已啟動。PID: {os.getpid()}。負責專案: {project_uuid}")
    print(f"將使用「可靠輪詢」模式，監控目錄: {project_path_to_watch}")

    # 我們用 flush() 確保日誌被立刻打印出來，而不是被緩存。
    sys.stdout.flush()

    # --- 【v5.4 核心改造】 ---
    # 我們創建一個「抖動抑制器」的實例，冷靜期設置為 2 秒。
    throttler = EventThrottler(delay=2.0)
    # 在創建事件處理器時，把 「抖動抑制器」跟 project_uuid 也傳進去。
    event_handler = SentryEventHandler(throttler=throttler, project_uuid=project_uuid)

    observer = PollingObserver(timeout=2)
    
    observer.schedule(event_handler, project_path_to_watch, recursive=True)
    
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n收到退出信號，正在停止觀察者...")
    finally:
        observer.stop()
        observer.join()
        print("觀察者已成功停止。")


# 這是一個 Python 的標準寫法。
if __name__ == "__main__":
    main()
