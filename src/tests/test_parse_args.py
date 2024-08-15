from shellsy.exceptions import *
from shellsy.settings import *
from shellsy.lexer import *
from shellsy.shell import *
from shellsy.shellsy import *
from shellsy.help import *
from shellsy.interpreter import *


def test_parse_args():
    interp = S_Interpreter()
    interp.eval("echo 3")
    interp.eval("echo 3:3")
    interp.eval("echo 3.5")
    interp.eval(r"echo '5.4\'r'")
    interp.eval("echo /C:/ama/")
    interp.eval("echo [1 2 3]")
    interp.eval("echo [1 2 [3] [] [-] [-a 3 -b 5]]")
