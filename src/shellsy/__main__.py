import sys
from shellsy.shellsy import Shellsy
from shellsy.settings import init


def main(*_):
    init()
    Shellsy()(sys.argv[1:])
