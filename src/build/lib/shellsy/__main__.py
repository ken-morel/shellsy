import sys
from shellsy.shellsy import shellsy
from shellsy.settings import init


def main(*_):
    init()
    shellsy()(sys.argv)
