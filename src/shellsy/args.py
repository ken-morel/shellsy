from inspect import _empty
from inspect import signature
from .lang import *
from typing import Any


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
            if string[pos] in ("'\""):
                quote = string[pos]
                text = quote
                pos += 1
                while pos < len(string):
                    if string[pos] == "\\":
                        if len(string) == pos + 1:
                            raise ShellsyNtaxError(
                                f"Escaped nothing at end of string:{string!r}"
                            )
                        elif string[pos + 1] in ("'\"\\"):
                            text += string[pos + 1]
                            pos += 2
                        else:
                            raise ShellsyNtaxError(
                                f"unknown escape {string[pos:pos+2]!r} in"
                                f" {string!r}"
                            )
                    elif string[pos] == quote:
                        pos += 1
                        break
                    else:
                        text += string[pos]
                        pos += 1
                string_parts.append(text + quote)
            elif string[pos] == "/":
                begin = pos
                pos += 1
                while pos < len(string) and not (
                    string[pos] == "/"
                    and (len(string) == pos + 1 or string[pos + 1].isspace())
                ):
                    pos += 1
                string_parts.append(string[begin : pos + 1])
            elif string[pos] == "(":
                chars = ("(", ")")
                begin = pos
                pos += 1
                stack = []
                while pos < len(string):
                    if string[pos] == ")" and len(stack) == 0:
                        break
                    elif string[pos] in chars[0]:
                        stack.append(string[pos])
                    elif string[pos] in chars[1]:
                        stack.pop()
                    pos += 1
                string_parts.append(string[begin : pos + 1])
            elif string[pos] == "{":
                chars = ("{", "}")
                begin = pos
                pos += 1
                stack = []
                while pos < len(string):
                    if string[pos] == "}" and len(stack) == 0:
                        break
                    elif string[pos] in chars[0]:
                        stack.append(string[pos])
                    elif string[pos] in chars[1]:
                        stack.pop()
                    pos += 1
                string_parts.append(string[begin : pos + 1])
            elif not string[pos].isspace():
                begin = pos
                while len(string) > pos and not string[pos].isspace():
                    pos += 1
                string_parts.append(string[begin:pos])
            pos += 1
        del pos
        return cls.from_string_parts(tuple(filter(bool, string_parts)))

    @classmethod
    @annotate
    def from_string_parts(cls, string_parts: Iterable[str]):
        args = []
        kwargs = {}

        def is_key(string):
            return string[0] == "-" and len(string) > 1 and string[1].isalpha()

        idx = 0
        while idx < len(string_parts):
            part = string_parts[idx]
            if is_key(part):
                key = part[1:]
                if idx + 1 < len(string_parts):
                    if is_key(string_parts[idx + 1]):
                        val = "Nil"
                    else:
                        val = string_parts[idx + 1]
                        idx += 1
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
        if len(string) > 0 and string[0] == "$":
            if ":" in string:
                varname, val = string[1:].split(":", 1)
                args = Variable(varname.strip()), evaluate_literal(val.strip())
            else:
                args = (Variable(string[1:].strip()),)
            return cls("var", Arguments(args, {}))
        else:
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
        if len(parts) == 0:
            name = ""
            args = []
        else:
            name, *args = parts
        return cls(name, Arguments.from_string_parts(args))

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
        for name, param in tuple(signature(func).parameters.items())[1:]:
            params.append(CommandParameter.from_inspect_parameter(param))
        return cls(params)

    @annotate
    def bind(self, args: Arguments) -> dict[str, Literal | Any]:
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
        final_args = {}
        for param, val in kwargs.items():
            if val == param.default:
                final_args[param.name] = val
                continue
            if isinstance(val, Variable) and param.type not in (
                _empty,
                Variable,
            ):
                val = val()
            if isinstance(val, Expression) and param.type not in (
                _empty,
                Expression,
            ):
                val = val()
            if param.type not in (_empty, Any) and not isinstance(
                val, param.type
            ):
                idx = -1
                if val in args.args:
                    idx = args.args.index(val)
                raise ArgumentTypeMismatch(param, val)
            final_args[param.name] = val
        return final_args

    def __str__(self):
        return f"<CommandParameters:[{', '.join(map(str, self.params))}]>"
