"""
Shellsy: An extensible shell program designed for ease of use and flexibility.

This module serves as the entry point for the Shellsy application, allowing
users
to define commands and interact with the shell environment.

Copyright (C) 2024 ken-morel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from dataclasses import dataclass
from inspect import Signature
from inspect import _empty
from inspect import signature
from pyoload import annotate
from typing import Any
from typing import Callable

from .lang import *
from .help import *
from .exceptions import NoSuchCommand, ArgumentError


@dataclass
@annotate
class S_Arguments(S_Object):
    __slots__ = ("args", "kwargs", "string")
    Val = tuple[Any, tuple[int, str]]
    Key = tuple[str, int]
    args: list[Val]
    kwargs: dict[Key, Val]
    string: str


@dataclass
@annotate
class CommandParameter:
    name: str
    type: Any
    default: Any
    mode: int

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
        s = self.name
        if self.type is not _empty:
            s += f": {self.type}"
        if self.default is not _empty:
            s += f" = {self.default}"
        return s + f", {mode}"

    def __hash__(self):
        return hash(self.name)


class CommandParameters:
    def __init__(self, params):
        self.params = params

    @classmethod
    def from_function(cls, func):
        return cls(
            [
                CommandParameter.from_inspect_parameter(p)
                for p in tuple(signature(func).parameters.values())[1:]
            ]
        )

    @annotate
    def bind(self, args: S_Arguments) -> dict[str, S_Literal]:
        kwargs = {}
        for idx, (val, (pos, raw)) in enumerate(args.args):
            if idx >= len(self.params):
                raise ArgumentError(
                    f"Extra positional argument",
                    args.string,
                    pos,
                    raw,
                )
            param = self.params[idx]
            kwargs[param] = ((pos, raw), val)

        for (key, pos), (val, (pos, raw)) in args.kwargs.items():
            for x in self.params:
                if x.name == key:
                    param = x
                    break
            else:
                raise ArgumentError(
                    f"Extra keyword argument",
                    args.string,
                    pos,
                    raw,
                )
            if param in kwargs:
                raise ArgumentError(
                    f"Keyword argument: {param} received. but was already "
                    "set (surely in positional parameters)",
                    args.string,
                    pos,
                    raw,
                )
            kwargs[param] = ((pos, raw), val)

        for idx, param in enumerate(self.params):
            if param not in kwargs:
                raise ArgumentError(
                    f"missing argument for {param}", args.string, 0, args.string
                )

        final_args = {}
        for param, ((pos, text), val) in kwargs.items():
            if val == param.default:
                final_args[param.name] = val
                continue
            if param.type not in (_empty, Any) and not type_match(val, param.type)[0]:
                raise ArgumentError(
                    f"Argument {val!r} invalid for param {param}",
                    args.string,
                    pos,
                    text,
                )
            final_args[param.name] = val
        return final_args

    def __str__(self):
        return f"_({', '.join(map(str, self.params))})"


@annotate
class Command:
    params: CommandParameters
    dispatches: "list[Command]"
    __func__: Callable
    help: CommandHelp
    name: str
    signature: Signature

    def __init__(self, func: Callable):
        from inspect import signature

        self.params = CommandParameters.from_function(func)
        self.__func__ = func
        self.name = func.__name__
        self.signature = signature(func)
        self.help = CommandHelp.from_command(self)
        self.dispatches = []

    @annotate
    def __call__(self, args: "S_Arguments"):
        if self.shell is None:
            raise RuntimeError(self, "was not attributed a shell")
        if len(self.dispatches) == 0:
            args = self.params.bind(args)
            return self.__func__(self.shell, **args)
        else:
            errors = []
            for cmd in [self] + self.dispatches:
                try:
                    args = cmd.params.bind(args, should_dispatch=True)
                except ShouldDispath as e:
                    errors.append(e.exception)
                    continue
                else:
                    return cmd.__func__(self.shell, **args)
            else:
                raise NoSuchCommand(
                    "No dispatch matches arguments\n" + "\n - ".join(map(str, errors))
                )

    def __set_name__(self, cls, name):
        self.name = name

    def dispatch(self, func):
        self.dispatches.append(Command(func))


class Shell:
    def __init_subclass__(cls):
        if not hasattr(cls, "name"):
            cls.name = cls.__name__.lower()
        if not hasattr(cls, "subshells"):
            cls.subshells = {}
        if not hasattr(cls, "commands"):
            cls.commands = {}

    def __init__(self, parent):
        self.parent = parent
        self.shellsy = parent.shellsy

        for attr in dir(self):
            if attr == "__entrypoint__":
                self.commands["__entrypoint__"] = getattr(self, attr)
            if attr.startswith("__"):
                continue
            try:
                if isinstance(cmd := getattr(self, attr), Command):
                    cmd.shell = self
                    if attr[0] == "_":
                        attr = attr[1:]
                    self.commands[attr] = cmd
                elif issubclass(subcls := getattr(self, attr), Shell):
                    if attr[0] == "_":
                        attr = attr[1:]
                    self.subshells[attr] = subcls(self)
            except (AttributeError, TypeError):
                pass

    def get_possible_subcommands(self):
        possible = list(self.commands)
        for sub, val in self.subshells.items():
            possible.extend([sub + "." + x for x in val.get_possible_subcommands()])
        return possible

    @annotate
    def get_command(self, cmd: str):
        if cmd == "":
            if "__entrypoint__" in self.commands:
                return self.commands["__entrypoint__"]
            else:
                raise NoSuchCommand(f"{self.name} has no entry point")
        else:
            if "." in cmd:
                name, inner = cmd.split(".", 1)
            else:
                name, inner = cmd, None
            if name in self.commands:
                return self.commands[name]
            elif name in self.subshells:
                return self.subshells[name].get_command(inner or "")
            else:
                raise NoSuchCommand(f"no such subcommand to get {name!r}")

    def run_file(self, path):
        with open(path) as f:
            try:
                for line in f:
                    line = line.strip()
                    self.stacktrace.clear()
                    self.stacktrace.add(
                        content=line,
                        parent_pos=(1, 0),
                        parent_text=None,
                        file=f"<{path}>",
                    )
                    if len(line) == 0 or line[0] == "#":
                        continue
                    else:
                        try:
                            val = self(line)
                        except ShouldDispath:
                            pass
                        else:
                            self.context["_"] = val
                            self.context["out"].append(val)
                            pprint(f"@{len(context['out']) - 1}>", val)
            except ShellsyException as e:
                e.show()
        return self.context["_"]

    def import_subshell(self, name, as_=None):
        from importlib import import_module

        mod = import_module(name + ".shellsy")
        try:
            plugin_shell = mod.shellsy
        except AttributeError as e:
            raise ShellNotFound(name + " has no shell: " + str(e)) from e
        else:
            from shellsy.lexer import for_shell

            self.subshells[as_ or name] = plugin_shell(parent=self)
            self.master._lexer = plugin_shell._lexer = for_shell(self.master)
            return plugin_shell
