import sys
from shellsy.shellsy import Shellsy
from shellsy.settings import init


def main(*_):
    init()
    if len(sys.argv) >= 2:
        Shellsy().run_file(sys.argv[1])
    else:
        Shellsy().cmdloop()
