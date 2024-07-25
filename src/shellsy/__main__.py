import sys, os
from shellsy.shellsy import Shellsy
from shellsy.settings import init


def main(*_):
    init()
    Shellsy()(sys.argv[1:])

n = 9
