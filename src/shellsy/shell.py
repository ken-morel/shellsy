"""
Shell.py, holds THe shell-related classes
including Shell, S_Arguments

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
class S_Arguments(S_Object):
    """
    Holds the arguments and code mappings to command call, has:

    - **args**: `list[tuple[Any, tuple[int, str]]]`: the list of tuples
      (`value`, (`pos`, `raw`)) mappings
    - **kwargs**: `dict[tuple[str, int], tuple[Any, tuple[int, str]]]`:
      the dictionnary mapping of tuples (`key`, `pos`) to
      (`value`, (`pos`, `raw`)) mappings
    - **string**: `str`: holds the raw arguments string
    """
    __slots__ = ("args", "kwargs", "string")
    Val = tuple[Any, tuple[int, str]]
    Key = tuple[str, int]
    args: list[Val]
    kwargs: dict[Key, Val]
    string: str


@dataclass
class CommandParameter:
    """
    Contains an instance of a command parameter, holds

    - **name**: `str`: the name of the parameter
    - **type**: `Any`: the type of the parameter
    - **default**: `Any`: the default value to the parameter
    - **mode**: `int`: the mode of parameter, from
      - **0**: positional only
      - **1**: positional or keyword
      - **0**: keyword only
    """
    name: str
    type: Any
    default: Any
    mode: int

    @classmethod
    def from_inspect_parameter(cls, param):
        """
        Creates a CommandParameter from inspect parameter instance

        :param param: THe inspect parameter
        :returns: THe CommandParameter instance
        """
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
    """
    Holds a list of command parameters for the command
    """
    params: list[CommandParameter]

    def __init__(self, params):
        """
        Create th command parameters
        :param params: The CommandParameter instances
        """
        self.params = params

    @classmethod
    def from_function(cls, func):
        """
        Gets the commandparameters for a function from it's inspect signature
        :param func: The function to get signature from
        :returns: Th CommandParameters
        """
        return cls(
            [
                CommandParameter.from_inspect_parameter(p)
                for p in tuple(signature(func).parameters.values())[1:]
            ]
        )

    def bind(self, args: S_Arguments) -> dict[str, S_Literal]:
        """
        binds the given arguments to the contained parameters

        :param args: The `S_Arguments` instance to bind
        :returns: A dictionarry mapping of names to values
        """
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
            if not type_match(val, param.type):
                if param.type == S_Literal and hasattr(val, "__shellsy_evaluatable__"):
                    val = val()
                else:
                    raise ArgumentError(
                        (
                            f"Argument {val!r} of type {type(val)!r}"
                            f" invalid for param {param}"
                        ),
                        args.string,
                        pos,
                        text,
                    )
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


class Command:
    """
    Holds a command instance and all it's dispatches
    """
    params: CommandParameters
    dispatches: "list[Command]"
    __func__: Callable
    help: CommandHelp
    name: str
    signature: Signature

    def __init__(self, func: Callable, shell: "Optional[Shell]" = None):
        """
        Creates, initializes the Command with the given function.
        :param func: THe function to construct command from
        :param shell: optionally specify the shell(when it is a method of a
        shell, the shell does this for You)
        """
        from inspect import signature

        self.params = CommandParameters.from_function(func)
        self.__func__ = func
        self.name = func.__name__
        self.signature = signature(func)
        self.help = CommandHelp.from_command(self)
        self.dispatches = []
        self.shell = shell

    def __call__(self, args: "S_Arguments"):
        """
        Calls the Command with the given arguments
        :param args: THe arguments
        :raises RuntimeError: raised if the parent shell not yet set
        """
        if self.shell is None:
            raise RuntimeError(self.name, "was not attributed a shell")
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

    def dispatch(self, func: Callable):
        """
        Decorator to create a dispatch of the default command function, called
        if arguments fail from binding.
        :param func: THe function to add
        """
        self.dispatches.append(Command(func))
        return func


class Shell:
    """
    The base of shelsy, a shell instance holds subshells, and commands,
    what you will subclass.
    """
    name: str
    parent: "Shell"
    shellsy: "Shell"

    def __init_subclass__(cls):
        if not hasattr(cls, "name"):
            cls.name = cls.__name__.lower()
        if not hasattr(cls, "subshells"):
            cls.subshells = {}
        if not hasattr(cls, "commands"):
            cls.commands = {}

    def __init__(self, parent: "Shell"):
        """
        Initializes the shell instance
        :param parent: THe parent shell, usually a Shellsy() instance.
        """
        self.parent = parent
        self.shellsy = parent.shellsy

        for attr in dir(self):
            if attr == "__entrypoint__":
                cmd = getattr(self, attr)
                cmd.shell = self
                self.commands["__entrypoint__"] = cmd
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

    def get_interpreter(self):
        """
        Gets the shell interpreter from parent
        :returns: THe interpreter instance
        """
        return self.shellsy.get_interpreter()

    def set_interpreter(self, interp):
        """
        sets the Shellsy instances interpreter

        :param interp: The new nterpreter
        """
        self._interpreter = interp

    def get_possible_subcommands(self):
        possible = list(self.commands)
        for sub, val in self.subshells.items():
            possible.extend([sub + "." + x for x in val.get_possible_subcommands()])
        return possible

    def get_command(self, cmd: str):
        """Recursively gets a command from dot sepperated subshell names
        :param cmd: THe command path
        :raises NoSuchCommand: The command name does not exist
        """
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

    def import_subshell(self, name: str, as_: 'Optional[str]' = None):
        """
        Imports the module {name}.shellsy, and saves the shellsy class in
        th specified name.

        :param name: THe package name to import
        :param as_: The subshell name to assign

        :returns: The plugin shell instance

        :raises ShellNotFound: THe shell could not be imported
        """
        from importlib import import_module

        mod = import_module(name + ".shellsy")
        try:
            plugin_shell = mod.shellsy
        except AttributeError as e:
            raise ShellNotFound(name + " has no shell: " + str(e)) from e
        else:
            from shellsy.lexer import for_shell
            shell = plugin_shell(parent=self)
            self.subshells[as_ or name.split(".", 1)[0]] = shell
            return shell
