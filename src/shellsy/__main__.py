import sys
from shellsy.shellsy import Shellsy
from shellsy.settings import init


def main(*_):
    init()
    if len(sys.argv[1:]) > 0:
        Shellsy()(sys.argv[1:])
    else:
        Shellsy().cmdloop()
