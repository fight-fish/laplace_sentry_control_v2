# src/core/sentry_worker.py (v9.1 - 重生版)

import sys
import time
import os
import signal
import json
from typing import Set, Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

# -----------------------------------------------------------------------------
# 核心配置
# -----------------------------------------------------------------------------
signal.signal(signal.SIGINT, signal.SIG_IGN)
SENTRY_INTERNAL_IGNORE = ('.sentry_status', 'temp', 'README.md', 'logs', 'data', '.git', '__pycache__', '.venv', '.vscode')
# 專案自身根目錄（用來偵測「自我監控」）
# -----------------------------------------------------------------------------
# SmartThrottler: 智能抑制器 (v1.0 - 重生版)
# -----------------------------------------------------------------------------
class SmartThrottler:
    """
    一個全新的、基於「可觀測指標」的智能抑制器。
    它不再關心事件的「次數」，而是關心「結構性」和「物理性」的異常。
    """
    def __init__(self,
            burst_creation_threshold: int = 20,
            burst_creation_period_seconds: float = 10.0,
            size_growth_threshold_mb: int = 100,
            size_growth_period_seconds: float = 60.0):
        
                # --- R1: 單檔過熱規則 ---
        self.hot_threshold = 3                     # 同一檔案在時間窗內允許的最大事件數
        self.hot_period = timedelta(seconds=5.0)   # 時間窗長度（秒）
        self.hot_events: Dict[str, List[datetime]] = {}  # {file_path: [timestamp1, ...]}

        # --- R3: 爆量創建規則 ---
        self.burst_creation_threshold = burst_creation_threshold
        self.burst_creation_period = timedelta(seconds=burst_creation_period_seconds)
        self.creation_timestamps: Dict[str, List[datetime]] = {} # {dir_path: [timestamp1, ...]}

        # --- R4: 體積異常規則 ---
        self.size_growth_threshold_bytes = size_growth_threshold_mb * 1024 * 1024
        self.size_growth_period = timedelta(seconds=size_growth_period_seconds)
        self.size_history: Dict[str, List[Tuple[datetime, int]]] = {} # {file_path: [(ts, size), ...]}

        # --- 通用靜默黑名單 ---
        self.muted_paths: Set[str] = set()



    def should_process(self, event) -> bool:
        """
        判斷一個事件是否應該被處理。
        """
        path = event.src_path
        now = datetime.now()

        # --- 【診斷探針 v1.0】 ---
        print(f"🕵️ PID:{os.getpid()} [{now.strftime('%H:%M:%S.%f')}] 收到事件: {event.event_type} @ '{os.path.basename(path)}'")
        sys.stdout.flush()

        # 1. 【通用規則】如果路徑或其父目錄已在靜默名單中，立刻拒絕
        if path in self.muted_paths or os.path.dirname(path) in self.muted_paths:
            print(f"  -> 決策: 拒絕 (路徑已在靜默黑名單中)")
            sys.stdout.flush()
            return False

        # 2. 【R1 規則檢測：單檔事件過熱】
        if event.event_type == 'modified':
            timestamps_r1 = self.hot_events.get(path, [])
            valid_timestamps_r1 = [t for t in timestamps_r1 if now - t < self.hot_period]
            valid_timestamps_r1.append(now)
            self.hot_events[path] = valid_timestamps_r1

            print(f"  -> R1 計數: 文件 '{os.path.basename(path)}' 的修改事件計數為 {len(valid_timestamps_r1)} / {self.hot_threshold}")
            sys.stdout.flush()

            if len(valid_timestamps_r1) >= self.hot_threshold:
                print(f"🔥 [智能靜默 R1] 偵測到文件 '{path}' 在短時間內事件過多，已將其臨時靜默。")
                self.muted_paths.add(path)
                if path in self.hot_events:
                    del self.hot_events[path]
                return False


        # 3. 【R3 規則檢測：爆量創建】
        if event.event_type == 'created':
            dir_path = os.path.dirname(path)
            timestamps = self.creation_timestamps.get(dir_path, [])
            valid_timestamps = [t for t in timestamps if now - t < self.burst_creation_period]
            valid_timestamps.append(now)
            self.creation_timestamps[dir_path] = valid_timestamps
            
            print(f"  -> R3 計數: 目錄 '{os.path.basename(dir_path)}' 的創建事件計數為 {len(valid_timestamps)} / {self.burst_creation_threshold}")
            sys.stdout.flush()

            if len(valid_timestamps) > self.burst_creation_threshold:
                print(f"🔥 [智能靜默 R3] 偵測到目錄 '{dir_path}' 發生爆量創建，已將其臨時靜默。")
                self.muted_paths.add(dir_path)
                return False


        # 4. 【R4 規則檢測：體積異常】
        if event.event_type == 'modified':
            try:
                current_size = os.stat(path).st_size
                history = self.size_history.get(path, [])
                valid_history = [h for h in history if now - h[0] < self.size_growth_period]
                
                initial_size = valid_history[0][1] if valid_history else 0
                growth = current_size - initial_size
                
                print(f"  -> R4 檢測: 文件 '{os.path.basename(path)}' 體積增長 {growth / (1024*1024):.2f} MB / {self.size_growth_threshold_bytes / (1024*1024):.2f} MB")
                sys.stdout.flush()

                if valid_history and growth > self.size_growth_threshold_bytes:
                    print(f"🔥 [智能靜默 R4] 偵測到文件 '{path}' 體積異常增長，已將其臨時靜默。")
                    self.muted_paths.add(path)
                    return False
                
                valid_history.append((now, current_size))
                self.size_history[path] = valid_history
            except (FileNotFoundError, IndexError):
                self.size_history[path] = [(now, current_size)]
            except Exception as e:
                print(f"⚠️ [SmartThrottler] 在檢查文件體積時出錯: {e}", file=sys.stderr)

        # 5. 如果所有檢查都通過，則允許處理
        print(f"  -> 最終決策: 放行")
        sys.stdout.flush()
        return True

# -----------------------------------------------------------------------------
# HACK: 專案路徑導入
# -----------------------------------------------------------------------------
project_root_for_import = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root_for_import not in sys.path:
    sys.path.insert(0, project_root_for_import)

from src.core import daemon

# -----------------------------------------------------------------------------
# SentryEventHandler: 哨兵事件處理器 (v9.1 - 重生版)
# -----------------------------------------------------------------------------
class SentryEventHandler(FileSystemEventHandler):
    def __init__(self, throttler: SmartThrottler, project_uuid: str, output_file_paths: Optional[List[str]] = None):
        self.throttler = throttler
        self.project_uuid = project_uuid
        self._last_muted_paths_state: Set[str] = set()
        # 【OUTPUT-FILE-BLACKLIST 機制】存儲輸出文件路徑的黑名單
        self.output_file_paths = set(output_file_paths) if output_file_paths else set()


    def on_any_event(self, event):
        # 步驟 1: 【R5 規則：結構性防火牆】
        if event.is_directory:
            return
        if isinstance(event.src_path, str):
            # 我們將 SENTRY_INTERNAL_IGNORE 檢查，放到所有邏輯的最前面
            normalized_path = os.path.normpath(event.src_path)
            path_parts = normalized_path.split(os.sep)
            if any(part in SENTRY_INTERNAL_IGNORE for part in path_parts):
                return # 靜默地、無情地忽略
            
        # 【OUTPUT-FILE-BLACKLIST 機制】過濾輸出文件的事件
        # 理由:防止系統寫入 output_file 時觸發的事件,造成監控迴圈。
        if normalized_path in self.output_file_paths:
            return  # 靜默地忽略輸出文件的所有事件


        # 步驟 2: 調用全新的智能抑制器
        should_proceed = self.throttler.should_process(event)

        # 步驟 3: 【無條件】檢查並更新郵箱狀態
        self._check_and_update_status_file()

        # 步驟 4: 根據決策執行核心動作
        if should_proceed:
            print(f"[{time.strftime('%H:%M:%S')}] [安全事件] 偵測到: {event.event_type} - 路徑: {event.src_path}")
            sys.stdout.flush()
            daemon.handle_manual_update([self.project_uuid])

# 請用這個版本，完整替換掉您當前代碼中的 _check_and_update_status_file 方法

    def _check_and_update_status_file(self):
        """檢查靜默列表是否有變，若有，則更新狀態文件（郵箱）。"""
        current_muted_paths = self.throttler.muted_paths
        if current_muted_paths != self._last_muted_paths_state:
            print(f"📫 [{time.strftime('%H:%M:%S')}] [情報更新] 靜默列表變化，正在寫入郵箱: {list(current_muted_paths)}")
            sys.stdout.flush()
            
            status_file_path = f"/tmp/{self.project_uuid}.sentry_status"
            
            try:
                with open(status_file_path, 'w', encoding='utf-8') as f:
                    json.dump(list(current_muted_paths), f)
                
                # --- 【診斷探針 v2.0】 ---
                # 我們在成功寫入後，補上這條關鍵的「成功回執」！
                print(f"✅ [{time.strftime('%H:%M:%S')}] 郵箱寫入成功: {status_file_path}")
                sys.stdout.flush()

                self._last_muted_paths_state = current_muted_paths.copy()

            except IOError as e:
                print(f"❌ [{time.strftime('%H:%M:%S')}] 寫入郵箱失敗: {e}", file=sys.stderr)

# -----------------------------------------------------------------------------
# main: 哨兵工人的主入口 (v9.1 - 重生版)
# -----------------------------------------------------------------------------
def main():
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("用法: python sentry_worker.py <project_uuid> <project_path> [output_files]", file=sys.stderr)
        sys.exit(1)

    project_uuid = sys.argv[1]
    project_path_to_watch = sys.argv[2]

    # 【OUTPUT-FILE-BLACKLIST 機制】接收輸出文件黑名單
    output_files_str = sys.argv[3] if len(sys.argv) == 4 else ''
    # 我們將逗號分隔的字符串,拆分回列表。空字符串會得到空列表。
    output_file_paths = [p.strip() for p in output_files_str.split(',') if p.strip()]


    if not os.path.exists(project_path_to_watch):
        print(f"錯誤: 監控路徑 '{project_path_to_watch}' 不存在。", file=sys.stderr)
        sys.exit(1)

    print(f"哨兵工人已啟動。PID: {os.getpid()}。負責專案: {project_uuid}")
    print(f"將使用「可靠輪詢」模式，監控目錄: {project_path_to_watch}")
    sys.stdout.flush()

        # 【OUTPUT-FILE-BLACKLIST 診斷】顯示接收到的黑名單
    if output_file_paths:
        print(f"【OUTPUT-FILE-BLACKLIST】已加載 {len(output_file_paths)} 個輸出文件到黑名單:")
        for path in output_file_paths:
            print(f"  - {path}")
    else:
        print("【OUTPUT-FILE-BLACKLIST】未接收到任何輸出文件黑名單")
    sys.stdout.flush()


    # 我們創建一個全新的、使用默認規則的 SmartThrottler
    throttler = SmartThrottler()
    
    event_handler = SentryEventHandler(throttler=throttler, project_uuid=project_uuid, output_file_paths=output_file_paths)

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

if __name__ == "__main__":
    main()
