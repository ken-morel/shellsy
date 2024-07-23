from argparse import ArgumentParser
from argparse import Namespace
from pyoload import *
from typing import Callable
from typing import Iterable
from typing import Type


class Param:
    def __init__(self, *args, **kw):
        self.args = args
        self.kw = kw

    def __call__(self, parser: ArgumentParser):
        parser.add_argument(*self.args, **self.kw)


class Parameters:
    params: Iterable[Param]
    parser: ArgumentParser

    # @annotate
    def __init__(self, *params: Iterable[Param]):
        self.params = params
        self.parser = ArgumentParser()

        for param in params:
            param(self.parser)

    @annotate
    def __call__(self, args: Iterable[str]) -> Namespace:
        return self.parser.parse_args(args)


@annotate
def group(text: str) -> list[str]:
    args = []
    pos = 0
    while pos < len(text):
        while pos < len(text):
            c = text[pos]
            if c in ("'", '"'):
                pos += 1
                begin = pos
                while pos < len(text):
                    if text[pos] == "\\":
                        pos += 2
                    elif text[pos] in ("'", '"'):
                        pos += 2
                        break
                    else:
                        pos += 1
                end = pos - 1
                args.append(text[begin:end])
            elif c.isspace():
                continue
            else:
                begin = pos
                while pos < len(text) and not text[pos].isspace():
                    pos += 1
                end = pos
                pos += 1
                args.append(text[begin:end])
    return args
