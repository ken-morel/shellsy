from inspect import _empty
from inspect import signature
from .lang import *
from typing import Any


class ShouldDispath(ValueError):
    def __init__(self, exc):
        self.exception = exc


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
        return f"{self.command}{self.arguments}"


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
        return f"{self.name}: {self.type} = {self.default}, {mode}"


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
    def bind(
        self, args: Arguments, should_dispatch: bool = False
    ) -> dict[str, Literal | Any]:
        kwargs = {}
        for idx, param in enumerate(self.params):
            if param.name in args.kwargs:
                kwargs[param] = args.kwargs[param.name]
            elif len(args.args) > idx:
                kwargs[param] = args.args[idx]
            elif param.default is not _empty:
                kwargs[param] = param.default
            else:
                if should_dispatch:
                    raise ShouldDispath(
                        ArgumentError(f"missing argument for {param}")
                    )
                else:
                    raise ArgumentError(f"missing argument for {param}")
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
                if should_dispatch:
                    raise ShouldDispath(ArgumentTypeMismatch(param, val))
                else:
                    raise ArgumentTypeMismatch(param, val)
            final_args[param.name] = val
        return final_args

    def __str__(self):
        return f"_({', '.join(map(str, self.params))})"
