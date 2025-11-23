import sys
import os
import json
import tkinter as tk
from tkinter import messagebox

# --- 1. 路徑黑魔法 (讓 UI 找得到後端) ---
# 我們現在在 src/ui/，需要往上兩層找到專案根目錄
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 2. 嘗試導入後端 ---
try:
    from src.core import daemon
    STATUS = "後端連接成功 (Daemon Imported)"
    COLOR = "green"
except Exception as e:
    STATUS = f"後端連接失敗: {e}"
    COLOR = "red"

# --- 3. 定義按鈕動作 ---
def load_data():
    try:
        # 直接呼叫後端函式
        projects = daemon.handle_list_projects()
        
        # 把結果轉成漂亮的 JSON 字串
        text_content = json.dumps(projects, indent=2, ensure_ascii=False)
        
        # 顯示在視窗上
        text_area.delete(1.0, tk.END) # 清空舊內容
        text_area.insert(tk.END, text_content)
        status_label.config(text="數據載入成功！", fg="blue")
        
    except Exception as e:
        messagebox.showerror("錯誤", f"調用後端失敗：\n{e}")

# --- 4. 建立最簡單的視窗 ---
root = tk.Tk()
root.title("UI 探針 (Backend Probe)")
root.geometry("600x400")

# 狀態標籤
status_label = tk.Label(root, text=STATUS, fg=COLOR, font=("Arial", 12, "bold"))
status_label.pack(pady=10)

# 載入按鈕
btn = tk.Button(root, text="呼叫 daemon.handle_list_projects()", command=load_data, height=2)
btn.pack(fill='x', padx=20)

# 顯示區域
text_area = tk.Text(root, height=15)
text_area.pack(fill='both', expand=True, padx=20, pady=10)

# 啟動
root.mainloop()