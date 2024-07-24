from .types import *
from inspect import _empty
from inspect import ismethod
from inspect import signature
from pyoload import *
from typing import Callable
from typing import Iterable
from typing import Type


class Literal:
    pass


class Int(Literal, int):
    @classmethod
    def from_string(cls, str):
        return cls(str)


class Float(Literal, Decimal):
    @classmethod
    def from_string(cls, str):
        return cls(str)


class Str(Literal, str):
    @classmethod
    def from_string(cls, str):
        return cls(str)


@annotate
def evaluate_literal(string: str) -> Literal:
    digits = set("01234567890eE")
    decimals = digits | set(".")
    string_quotes = set("'\"")
    string_set = set(string)

    if len(string_set - digits) == 0:
        return Int(string)
    elif len(string_set - decimals) == 0:
        return Float(string)
    elif string[0] in string_quotes:
        if string[0] != string[-1]:
            raise SyntaxError("unterminated string literal")
        return Str(string[1:-1])
    raise ValueError(string)


class Arguments:
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return f"({self.args}, {self.kwargs})"

    @classmethod
    @annotate
    def from_string(cls, string: str):
        pos = 0
        string_parts = [""]
        # split string
        while pos < len(string):
            if string[pos].isspace():
                string_parts.append("")
            else:
                string_parts[-1] += string[pos]
            pos += 1
        del pos
        return cls.from_string_parts(tuple(filter(bool, string_parts)))

    @classmethod
    @annotate
    def from_string_parts(cls, string_parts: Iterable[str]):
        args = []
        kwargs = {}
        # split literals
        idx = 0
        while idx < len(string_parts):
            part = string_parts[idx]
            if part[0] == "-":
                key = part[1:]
                idx += 1
                if idx < len(string_parts):
                    val = string_parts[idx]
                else:
                    raise ValueError()
                kwargs[key] = val
            else:
                args.append(part)
            idx += 1
        # evaluate literals
        args = tuple(map(evaluate_literal, args))
        kwargs = dict(zip(kwargs, map(evaluate_literal, kwargs.values())))
        return Arguments(args, kwargs)


@annotate
class CommandCall:
    command: str
    arguments: Arguments

    def __init__(self, cmd: str, args: Arguments):
        self.command = cmd
        self.arguments = args

    def inner(self):
        cmd, *rest = self.command.split(".")
        return cmd, CommandCall(".".join(rest), self.arguments)

    @classmethod
    @annotate
    def from_string(cls, string: str):
        cmd = ""
        args = ""
        pos = 0
        while pos < len(string) and (
            string[pos].isalnum() or string[pos] in "._"
        ):
            pos += 1
        cmd = string[:pos]
        args = string[pos:].strip()
        return cls(cmd, Arguments.from_string(args))

    @classmethod
    @annotate
    def from_string_parts(cls, parts: Iterable[str]):
        name, *args = parts
        return cls(name, args)

    def __str__(self):
        return f"<Command:{self.command}{self.arguments}>"


class CommandParameter:
    def __init__(self, name: str, type: None, default: None, mode: int):
        self.name = name
        self.type = type
        self.default = default
        self.mode = mode

    @classmethod
    def from_inspect_parameter(cls, param):
        mode = (
            param.POSITIONAL_ONLY,
            param.POSITIONAL_OR_KEYWORD,
            param.KEYWORD_ONLY,
        ).index(param.kind)
        return cls(param.name, param.annotation, param.default, mode)

    def __str__(self):
        mode = ("/", "/*", "*")[self.mode]
        return f"<{self.name}: {self.type} = {self.default}, {mode}>"


class CommandParameters:
    def __init__(self, params):
        self.params = params

    @classmethod
    def from_function(cls, func):
        params = []
        for name, param in signature(func).parameters.items():
            params.append(CommandParameter.from_inspect_parameter(param))
        if ismethod(func):
            params.pop(0)
        return cls(params)

    @annotate
    def bind(self, args: Arguments) -> dict[str, Literal]:
        kwargs = {}
        for idx, param in enumerate(self.params):
            if param.name in args.kwargs:
                kwargs[param] = args.kwargs[param.name]
            elif len(args.args) > idx:
                kwargs[param] = args.args[idx]
            elif param.default is not _empty:
                kwargs[param] = param.default
            else:
                raise ValueError(f"missing argument for {param}")

        for param, val in kwargs.values():
            if param.type is not _empty and not isinstance(val, param.type):
                raise TypeError(f"non matchin types from {val=} to {param=}")
        return kwargs

    def __str__(self):
        return f"<CommandParameters:[{', '.join(map(str, self.params))}]>"
