# src/core/formatter.py
# ==============================================================================
#  通用目錄哨兵 - 格式化專家 v1.0
# ==============================================================================
#
#  【核心職責】
#  作為一個獨立的、可插拔的「包裝部門」，它的唯一職責是接收一段純文本
#  內容，並根據指定的「格式化策略」，為其包裹上特定的語法格式，以適
#  配不同的終端（如 Obsidian, GitHub Flavored Markdown 等）。
#
#  【設計原則】
#  - 高度內聚：只關心「格式」，不關心「內容」。
#  - 低耦合：通過標準輸入/輸出與外界交互，不與任何其他專家產生直接依賴。
#  - 可擴展：未來支持新格式，只需在此處增加新的 `if/elif` 策略分支。
#
# ==============================================================================
import sys
import argparse

def main():
    """
    主執行函數，負責解析命令列參數並應用格式化策略。
    """
    # 1. 創建一個命令列參數翻譯官
    parser = argparse.ArgumentParser(description="為輸入的文本應用特定的格式化策略。")
    
    # 2. 告訴翻譯官，我們需要一個名叫 '--strategy' 的參數
    #    - default='raw'：如果使用者不提供這個參數，默認就使用 'raw' 策略。
    #    - help='...'：為使用者提供清晰的幫助說明。
    parser.add_argument(
        '--strategy', 
        default='raw', 
        help="要應用的格式化策略 (例如: 'obsidian', 'raw')"
    )
    
    # 3. 命令翻譯官開始工作，解析傳入的指令
    args = parser.parse_args()

    # 4. 從標準輸入 (stdin) 讀取由上一個專家（如 engine.py）傳來的、
    #    純淨的、未經格式化的「原材料」內容。
    raw_content = sys.stdin.read()

    # 5. 根據解析出的策略，進行不同的「包裝」操作
    if args.strategy == 'obsidian':
        # 如果是 'obsidian' 策略，就在原材料的頭尾，包裹上 Markdown 的代碼塊語法
        formatted_content = f"```\n{raw_content.strip()}\n```"
    else:
        # 默認的 'raw' 策略，不做任何改動，原樣輸出
        formatted_content = raw_content
    
    # 6. 將最終「包裝」好的成品，打印到標準輸出 (stdout)，
    #    以便下一個流程（如 worker.sh）可以接收和使用。
    print(formatted_content)

# 確保這個腳本是作為主程序直接執行時，才運行 main() 函式
if __name__ == "__main__":
    main()

