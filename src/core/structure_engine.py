# 我們用「def」來 定義 (define) 一個我們自己的函式。
def generate_tree():
    # 這個函式非常簡單，它只是「返回（return）」一段固定的文字。
    return "✅ 成功：來自『結構專家』(structure_engine.py) 的問候！"

# 這是一個 Python 的標準寫法。
# 它的意思是：只有當這個腳本被「直接執行」時，才去運行下面的程式碼。
if __name__ == "__main__":
    # 我們呼叫上面定義的函式，並把結果「打印（print）」到終端上。
    print(generate_tree())
