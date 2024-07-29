out = []
try:
    eval("++--++")
except SyntaxError as e:
    print(e.args)
