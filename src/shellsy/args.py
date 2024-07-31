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
        argmaps = []
        if len(string) > 0 and string[0] == "$":
            if "=" in string:
                varname, val = string[1:].split("=", 1)
                val = val.strip()
                argmaps.append((1, varname))
                argmaps.append((len(string) - len(val), val))
                args = Variable(varname.strip()), evaluate_literal(val)
            elif ":" in string:
                from .shell import Shell
                varname, val = string[1:].split(":", 1)
                val = val.strip()
                argmaps.append((1, varname))
                argmaps.append((len(string) - len(val), val))
                args = Variable(varname.strip()), Shell.master(val)
            else:
                argmaps.append((1, string[1:].strip()))
                args = (Variable(string[1:].strip()),)
            STACKTRACE.add(
                Stack(
                    content=string,
                    parent_pos=(1, 0),
                    parent_text=string,
                    file="<call>",
                )
            )
            return cls(
                "var",
                Arguments(
                    args, {}, full_string=string, kwmaps={}, argmaps=argmaps
                ),
            )
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
            STACKTRACE.add(
                Stack(
                    content=args,
                    parent_pos=(1, pos + 1),
                    parent_text=string,
                    file="<call>",
                )
            )
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
        STACKTRACE.add(
            Stack(
                content=args.full_string,
                parent_pos=(1, 0),
                parent_text=None,
                file=f"<arguments>",
            )
        )
        for idx, param in enumerate(self.params):
            if param.name in args.kwargs:
                kwargs[param] = (
                    args.kwmaps[param.name],
                    args.kwargs[param.name],
                )
            elif len(args.args) > idx:
                kwargs[param] = (args.argmaps[idx], args.args[idx])
            elif param.default is not _empty:
                kwargs[param] = ((1, ""), param.default)
            else:
                if should_dispatch:
                    raise ShouldDispath(
                        ArgumentError(
                            f"missing argument for {param}", STACKTRACE
                        )
                    )
                else:
                    raise ArgumentError(
                        f"missing argument for {param}", STACKTRACE
                    )
        final_args = {}
        for param, ((pos, text), val) in kwargs.items():
            STACKTRACE.add(
                Stack(
                    content=text,
                    parent_pos=(1, pos),
                    parent_text=args.full_string,
                    file=f"<argument>",
                )
            )
            if val == param.default:
                final_args[param.name] = val
                continue
            if isinstance(val, Variable) and (
                param.type
                not in (
                    _empty,
                    Variable,
                )
            ):
                val = val()
            if isinstance(val, Expression) and (
                param.type
                not in (
                    _empty,
                    Expression,
                )
                or val.auto_evaluate
            ):
                val = val()
            if isinstance(val, CommandBlock) and (
                param.type
                not in (
                    _empty,
                    CommandBlock,
                )
                or val.auto_evaluate
            ):
                val = val.evaluate()
            if param.type not in (_empty, Any) and not type_match(
                val, param.type
            ):
                idx = -1
                if val in args.args:
                    idx = args.args.index(val)
                if should_dispatch:
                    raise ShouldDispath(
                        ShellsyError(
                            f"Argument {val!r} invalid for param {param}",
                            STACKTRACE,
                        )
                    )
                else:
                    raise ShellsyError(
                        f"Argument {val!r} invalid for param {param}",
                        STACKTRACE,
                    )
            final_args[param.name] = val
        return final_args

    def __str__(self):
        return f"_({', '.join(map(str, self.params))})"
