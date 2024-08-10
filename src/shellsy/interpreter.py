"""
Shellsy: An extensible shell program designed for ease of use and flexibility.

This module serves as the entry point for the Shellsy application, allowing
users
to define commands and interact with the shell environment.

Copyright (C) 2024  Ken Morel

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

import rich
import rich.panel
import rich.syntax
import string

import lexer

from dataclasses import dataclass
from pyoload import annotate
from typing import Any
from typing import Callable
from inspect import Signature, signature
from pathlib import Path


class NoSuchCommand(ValueError):
    pass


@annotate
class StackTrace:
    """Maintains a list of Stack instances for error reporting."""

    @dataclass
    @annotate
    class Stack:
        """Represents a call stack for error reporting in the shell."""

        xpos: tuple[int, int]
        line: str
        file: str
        ypos: int = 0

        def show(self):
            b, e = self.xpos
            file_name = (
                f"[cyan]{self.file}[/cyan]"
                if self.file[0] == "<"
                else f"[blue underline]{self.file}[/blue underline]"
            )
            file_info = (
                f"File: {file_name}, line: [magenta]{self.ypos}"
                f"[/magenta], Column: [magenta]{b}[/magenta]:"
            )
            rich.print(rich.panel.Panel(file_info, title="[red]Error"))
            rich.print(
                rich.syntax.Syntax(
                    self.line,
                    lexer=lexer.lexer,
                    theme="monokai",
                )
            )
            rich.print(" " * b + "^" * (e - b))

    stacks: list[Stack]

    def __init__(self):
        self.stacks = []

    def add(self, begin: int, end: int, row: int, line: str, file: str):
        """add(self, begin: int, end: int, row: int, line: str, file: str):"""
        return self.add_stack(
            StackTrace.Stack(xpos=(begin, end), ypos=row, line=line, file=file)
        )

    def add_stack(self, stack):
        self.stacks.append(stack)

    def pop(self):
        if self.stacks:
            self.stacks.pop()

    def clear(self):
        self.stacks.clear()

    def show(self):
        """Display the entire stack trace."""
        for stack in self.stacks:
            stack.show()


@annotate
class ShellsyException(Exception):
    """Base class for exceptions in the Shellsy application."""

    stacktrace: StackTrace
    message: str

    def __init__(self, msg: str, stacktrace):
        self.stacktrace = stacktrace
        self.message = msg

    def show(self):
        self.stacktrace.show()
        print(f"Exception: {self.__class__.__name__} {self.message}")


class S_Object:
    __slots__ = ()


class S_int(S_Object, int):
    pass


class S_float(S_Object, float):
    pass


class S_str(S_Object, str):
    pass


class S_NameSpace(S_Object, dict):
    __slots__ = S_Object.__slots__


@dataclass
@annotate
class S_Arguments(S_Object):
    __slots__ = ("args", "kwargs", "string")
    Val = tuple[Any, tuple[int, str]]
    Key = tuple[str, int]
    args: list[Val]
    kwargs: dict[Key, Val]
    string: str


class Command:
    pass


class CommandArguments:
    pass


@annotate
class S_Command(S_Object):
    command: Command
    arguments: CommandArguments

    def evaluate(self):
        self.command.evaluate(self.arguments)


@annotate
class S_bool(S_Object):
    __slots__ = ("val",)
    _true = None
    _false = None
    val: bool

    def __new__(cls, val=False):
        val = bool(val)
        if val:
            if cls._true is None:
                cls._true = super().__new__(cls)
            return cls._true
        else:
            if cls._false is None:
                cls._false = super().__new__(cls)
            return cls._false

    def __init__(self, val: bool = False):
        self.val = val

    def __repr__(self):
        return repr(self.val)

    def __reduce__(self):
        return (self.__class__, ())

    def __bool__(self):
        return self.val


@annotate
class NilType(S_Object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "Nil"

    def __reduce__(self):
        return (self.__class__, ())

    def __bool__(self):
        return False

    def __instancecheck__(self, other):
        return other is Nil

    def __sub__(self, other):
        return other is Nil

    def __rsub__(self, other):
        return other is Nil


Nil = NilType()


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
        for idx, (val, (pos, raw)) in enumerate(zip(args.args, args.argmaps)):
            STACKTRACE.add(
                Stack(
                    content=raw,
                    parent_pos=(1, pos),
                    parent_text=args.full_string,
                    file=f"<argument>",
                )
            )
            if idx >= len(self.params):
                if should_dispatch:
                    raise ShouldDispath(
                        ArgumentError(
                            f"Extra positional argument",
                        )
                    )
                else:
                    raise ArgumentError(
                        f"Extra positional argument",
                    )
            param = self.params[idx]
            kwargs[param] = ((pos, raw), val)
            STACKTRACE.pop()

        for (key, val), (pos, raw) in zip(
            args.kwargs.items(), args.kwmaps.values()
        ):
            STACKTRACE.add(
                Stack(
                    content=raw,
                    parent_pos=(1, pos),
                    parent_text=args.full_string,
                    file=f"<argument>",
                )
            )
            for x in self.params:
                if x.name == key:
                    param = x
                    break
            else:
                if should_dispatch:
                    raise ShouldDispath(
                        ArgumentError(
                            f"Extra keyword argument",
                        )
                    )
                else:
                    raise ArgumentError(
                        f"Extra keyword argument",
                    )
            if param in kwargs:
                raise ArgumentError(
                    f"Keyword argument: {param} received. but was already "
                    "set (surely in positional parameters)",
                )
            kwargs[param] = ((pos, raw), val)
            STACKTRACE.pop()

        for idx, param in enumerate(self.params):
            if param not in kwargs:
                if param.default is not _empty:
                    kwargs[param] = param.default
                elif should_dispatch:
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
            if (
                param.type not in (_empty, Any)
                and not type_match(val, param.type)[0]
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


class CommandHelp:
    pass


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
    def __call__(self, shell: 'Shell', args: 'Arguments'):
        if len(self.dispatches) == 0:
            args = self.params.bind(args)
            return self.__func__(shell, **args)
        else:
            errors = []
            for cmd in [self] + self.dispatches:
                try:
                    args = cmd.params.bind(args, should_dispatch=True)
                except ShouldDispath as e:
                    errors.append(e.exception)
                    continue
                else:
                    return cmd.__func__(shell, **args)
            else:
                raise NoSuchCommand(
                    "No dispatch matches arguments\n"
                    + "\n - ".join(map(str, errors))
                )

    def __set_name__(self, cls, name):
        self.name = name

    def dispatch(self, func):
        self.dispatches.append(Command(func))


class Shell:
    def __init_subclass__(cls):
        if not hasattr(cls, 'name'):
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
            possible.extend(
                [sub + "." + x for x in val.get_possible_subcommands()]
            )
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
                return self.subshells[name].get_command(inner or '')
            else:
                raise NoSuchCommand(f"no such subcommand to get {name!r}")

    def run_file(self, path):
        with open(path) as f:
            try:
                for line in f:
                    line = line.strip()
                    STACKTRACE.clear()
                    STACKTRACE.add(
                        Stack(
                            content=line,
                            parent_pos=(1, 0),
                            parent_text=None,
                            file=f"<{path}>",
                        )
                    )
                    if len(line) == 0 or line[0] == "#":
                        continue
                    else:
                        try:
                            val = self(line)
                        except ShouldDispath:
                            pass
                        else:
                            context["_"] = val
                            context["out"].append(val)
                            pprint(f"@{len(context['out']) - 1}>", val)
            except ShellsyError as e:
                e.show()
        return context["_"]

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


class Shellsy(Shell):
    """
    Welcome, to shellsy, here you will build simple tools
    """

    intro = """shellsy  Copyright (C) 2024 ken-morel
This program comes with ABSOLUTELY NO WARRANTY; for details type `w_`.
This is free software, and you are welcome to redistribute it
under certain conditions; type `c_` for details."""

    @Command
    def cd(shell, path: Path = None):
        """
        The command to change working directory
        :param path: The path to the new working directory

        :returns: The new working directory
        """
        if path:
            try:
                os.chdir(path)
            except Exception as e:
                print(e)
        return Path(os.getcwd())

    chdir = cd

    class bookmark(Shell):
        @Command
        def __entrypoint__(shell, _: Word["as"], name: str):
            """\
            Bookmarks the current directory, or simply adds it to the bookmarks
            list
            :param name: The name to bookmark under
            """
            bookmarks = get_setting("bookmarks", {})
            bookmarks[name] = str(Path(".").resolve())
            set_setting("bookmarks", bookmarks)

        @__entrypoint__.dispatch
        def __entrypoint__2(shell, name: str):
            """\
            Bookmarks the current directory, or simply adds it to the bookmarks
            list
            :param name: The name of bookmark
            """
            bookmarks = get_setting("bookmarks", {})
            if name in bookmarks:
                os.chdir(bookmarks[name])
                StatusText("Moved to !", source="shellsy:.bookmark")
            else:
                print("No such bookmark!")
                return None

    @Command
    def mkdir(shell, path: Path = None):
        """
        The command utility to change directory
        :param path: The new path to assign

        :returns: The new working directory
        """
        try:
            os.makedirs(path)
        except Exception as e:
            print(e)
            return Nil
        else:
            return path

    @Command
    def dir(shell, pattern: str | Path = "*"):
        """
        The command utility to change directory
        :param path: The new path to assign

        :returns: The new working directory
        """
        from rich.markdown import Markdown
        from rich import print

        txt = ""
        for x in Path(".").resolve().glob(str(pattern)):
            txt += f"- {txt}\n"
        print(Markdown(txt))
        return tuple(Path(".").resolve().glob(str(pattern)))

    @Command
    def echo(shell, val):
        """
        Reproduces a value val

        :param val: the value to reproduce

        :returns: val
        """
        return repr(val)

    @Command
    def print(shell, val):
        """
        prints the passed value to stdout and returns None
        :param val: the value to print

        :returns: None
        """
        return print(repr(val))

    @Command
    def var(shell, var: Variable, val=None):
        """
        setts or gets a variable
        :param var: te variable
        :param val: optional value to sey

        :returns: The variable
        """
        if val is not None:
            var(val)
        return var

    @Command
    def eval(shell, var: Any):
        """
        Returns an evaluated literal
        :param var: The value to eval

        :returns: The evaluate
        """
        return var

    @Command
    def _if(
        shell,
        condition: Expression,
        then: CommandBlock,
        __: Word["else"] = None,
        else_: CommandBlock = None,
    ):
        """
            Evaluates a condition and executes a command block if the condition
             is met.
            If the condition is not met and an else block is provided,
            the else block is executed.

            :param condition: The condition to evaluate before executing the
            'then' block. It should be a function that returns a boolean value.
            :param then: The command block to execute if the condition is met.
             This block contains the commands to run when the condition is true
            :param else_: Optional - The command block to execute if the
            condition is not met. If provided, this block will be executed when
            the condition is false.

            :returns: The result of executing the 'then' block or the 'else'
            block if the condition is not met.

            For example:
            if (x > 5) {echo 'x > 5'} else {echo 'x <= 5'}

            [[2]](https://poe.com/citation?message_id=224987918374&citation=2)
        """
        if condition():
            return then.evaluate(shell)
        else:
            if else_ is not None:
                return else_.evaluate(shell)
            return None

    @Command
    def _while(
        shell,
        condition: Expression,
        then: CommandBlock,
    ):
        """
        The 'while' command in shellsy creates a loop that iterates as long as
        a specified condition is met. This command enables the repetitive
        execution of a block of commands until the condition evaluates to False

        :param condition: The condition parameter defines the expression to be
        evaluated in each iteration of the loop. The 'while' command will
        continue executing the associated block of commands as long as this
        condition remains True. It serves as the criteria for determining the
        loop's continuation

        :param then: The command_block parameter represents the block
        of commands that will be executed repeatedly as part of the 'while'
        loop. This block contains the actions or logic that should be performed
        iteratively until the condition evaluates to False. It encapsulates the
        commands to be executed within the loop structure

        :returns: The 'while' command does not have an explicit return value,
        as its primary function is to facilitate iterative execution based on
        the specified condition. The execution of the command_block within the
        loop allows for repetitive actions until the condition becomes False.
        The return value is determined by the commands executed within the loop

        Example usage:
        _while(lambda: x > 5, CommandBlock(...))

        Utilize the 'while' command in shellsy with the provided parameters and
        syntax to implement loops that perform repetitive actions based on
        defined conditions.
        This feature enhances the flexibility and functionality of your scripts
        by enabling iterative execution of commands until a specific condition
        is no longer met
        """
        ret = None
        while condition():
            ret = then.evaluate(shell)

        return ret

    class config(Shell):
        def __entrypoint__(shell, name: str, val: Any = None):
            """\
            config edit configuration settings.

            :param name: The name of the setting to get or set
            :param val: The optional value to assign.

            :returns: THe value of setting 'name'
            """
            if val is not None:
                set_setting(name, val)
            return get_setting(name)

    class status(Shell):
        @Command
        def __entrypoint__(shell):
            """\
            status command prints all the currently showing status messages

            :returns: None
            """
            for x in StatusText.showing:
                pprint(x)
            return None

        @Command
        def add(shell, text: str, dur: int = 5000, source: str = "shell"):
            """
            Creates a new status message in status bar

            :param text: The status text
            :param dur: the status text duration.
            :param source: THe source the status will be attributed.
            Another status of the same source will be overridden if exists.

            :returns: THe status text object
            """
            return StatusText(text, dur, source=source)

        @Command
        def clear(shell):
            """
            Clears all the shown status messages

            :returns: None
            """
            return StatusText.clear()

    class plugin(Shell):
        @Command
        def list(shell):
            """\
            List all available plugins in plugin directory.

            :returns: THe list of plugin names
            """
            from shellsy.plugin import Plugin

            txt = ""
            all = Plugin.list()
            for plug in all:
                txt += f"- {plug.name} at {plug.module.__file__}\n"
            if len(all) == 0:
                txt = "# No module here yet"
            pprint(Markdown(txt))
            return all

        @Command
        def init(
            shell,
            name: str,
            author: str,
            version: str = "1.0.0",
            path: Path = Path("."),
            author_email: str = "",
            description: str = "A sample shellsy plugin",
            requirements: list = [],
        ):
            """
            initializes a plugin. It creatres a shellsy plugin compatible
            with pip install mechnism, the plugin can then be:

            - Installed to site-packages via `pip install .`
            - Installed to shellsy plugin dir via `shellsy install`
            - Uploaded to pip, view info at [pypi](https://pypi.org/)

            :param name: the plugin name to create. Should match the
            requirements for a python package name. It should preferably be
            different from any other name available at https://pypi.org
            :param author: the plugin author
            :param version: the plugin version, using python versionin syntax
            with X.x.x, as in `1.0.0` or `3.9.7`
            :param path: the plugin path, should be the actuall directory
            :param description: the plugin description, should be not too long
            as more extensive explanation will be avilable in README.md
            :param requirements: the plugin requirements, a list of
            module specs, as [pyoload=2.0.2 comberload==1.1.0]

            :returns: nothing yet, just initializes the plugin
            """
            from shellsy.plugin import initialize_plugin

            return initialize_plugin(
                name=name,
                author=author,
                version=version,
                path=path,
                author_email=author_email,
                description=description,
                requirements=requirements,
            )

        @Command
        def install(shell, path: Path | str = "."):
            """
            Installs the plugin in the current working directory or from
            specified path or pypi package name

            :param path: The optional package name or location
            """
            import os
            from shellsy.settings import plugin_dir

            os.system(
                f'pip install {path} --target "{plugin_dir}" --upgrade'
            )

    @Command
    def _import(shell, name: str):
        """
        Loads the specified module by importing it
        :param name: The name of module to import

        :returns: THe plugin shell or `None` if fails import
        """
        try:
            shell.import_subshell(name)
        except (ImportError, ModuleNotFoundError) as e:
            print(e)

    @_import.dispatch
    def _import_as(shell, location: str, _: Word["as"], name: str):
        try:
            shell.import_subshell(location, as_=name)
        except (ImportError, ModuleNotFoundError) as e:
            print(e)

    @_import.dispatch
    def _import_or_install(
        shell,
        name: str,
        _: Word["or"],
        __: Word["install"],
        ___: Word["from"],
        location: str | Path,
    ):
        try:
            shell.import_subshell(name)
        except (ImportError, ModuleNotFoundError, ShellNotFound):
            try:
                e.show()
            except Exception:
                pass
            import os
            from shellsy.settings import plugin_dir

            os.system(
                "pip install "
                + str(location)
                + ' --target "'
                + str(plugin_dir)
                + '" '
                + "--upgrade"
            )
        finally:
            shell.import_subshell(name)

    class help(Shell):
        @Command
        def __entrypoint__(shell, command: str = None):
            if command:
                pprint(shell.master.get_command(command).help.markdown())
            else:
                log.error("no command specified")

    class json(Shell):
        @Command
        def load(shell, file: Path, var: Variable = None):
            """\
Deserialize a JSON formatted stream to a Python object.

:param fp: A file-like object containing a JSON document. The file object must
have a method called `read()`
           that returns a string containing the JSON data.
:param **kwargs: Additional keyword arguments that control the deserialization
process, such as:
                 - `object_hook`: (function) function that will be called with
                   the result of every JSON object
                   decoded; this can be useful for customizing the
                   deserialization of objects.
                 - `parse_float`: (function) function that will be called with
                   the string of every JSON float
                   to be decoded; this can be useful for customizing how floats
                   are parsed.
                 - `parse_int`: (function) function that will be called with
                   the string of every JSON int
                   to be decoded; this can be useful for customizing how ints
                   are parsed.

:returns: The resulting Python object.

:raises json.JSONDecodeError: If the JSON is malformed or cannot be decoded.
                """
            if not file.exists():
                log.error("file does not exist")
            text = file.read_text()
            try:
                data = json.loads(text)
            except Exception as e:
                log.error(e)
            else:
                if var is not None:
                    var.set(data)
                return data

        @Command
        def dump(shell, data: Any, file: Path = None, indent: int = None):
            """
Serialize a Python object to a JSON formatted string.

:param obj: The Python object to convert to a JSON string.
:param indent: Additional keyword arguments that control the serialization
                   process, such as:
                 - `indent`: (int) specifies the number of spaces for
                   indentation.
                 - `separators`: (tuple) customizes the item and key separator.
                 - `sort_keys`: (bool) if True, the output will be sorted by
                    keys.

:returns: A JSON formatted string representation of the object.
            """
            try:
                text = json.dumps(data, indent=indent)
            except Exception as e:
                log.error(e)
            else:
                if file is not None:
                    try:
                        file.write_text(text)
                    except Exception as e:
                        log.error("error writing to file: " + str(e))
                return text

    class yaml(Shell):
        @Command
        def load(shell, file: Path, var: Variable = None):
            try:
                import yaml
            except ImportError:
                return log.error("yaml not installed")
            if not file.exists():
                return log.error("file does not exist")
            text = file.read_text()
            try:
                data = yaml.safe_loads(text)
            except Exception as e:
                log.error(e)
            else:
                if var is not None:
                    var.set(data)
                return data

        @Command
        def dump(shell, data: Any, file: Path = None):
            try:
                import yaml
            except ImportError:
                return log.error("yaml not installed")
            try:
                text = yaml.safe_dump(data)
            except Exception as e:
                log.error(e)
            else:
                if file is not None:
                    try:
                        file.write_text(text)
                    except Exception as e:
                        log.error("error writing to file: " + str(e))
                return text

    @Command
    def exit(shell):
        shell.should_run = False

    @Command
    def w_(shell):
        """Shellsy waranty"""
        from rich.markdown import Markdown
        from rich import print
        print(Markdown("""# Warranty Disclaimer

This program is distributed in the hope that it will be useful,
but **WITHOUT ANY WARRANTY**; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

For more details, refer to the [GNU General Public License]
(https://www.gnu.org/licenses/gpl-3.0.html).

## Important Notes:
- You are advised to test the program extensively before using it in any
critical applications.
- The authors and contributors of this software are not responsible for any
damages that may occur through its use.
- If you encounter any issues, please consider reporting them to the respective
maintainers for potential improvements.

Thank you for using our software!"""))

    @Command
    def c_(shell):
        """Shellsy waranty"""
        from rich.markdown import Markdown
        from rich import print
        print(Markdown("""# License Information

This program is licensed under the **GNU General Public License (GPL)**.

## Key Points of the License:

- **Freedom to Use**: You are free to use this software for any purpose.
- **Access to Source Code**: You can view, modify, and distribute the source
  code.
- **Distribution**: When redistributing the software, you must provide the
  same license terms to others. This ensures that everyone can benefit from the
  freedoms granted by this license.

## Disclaimer:
- This software is provided "as is", without any warranty of any kind, express
  or implied.
- For more details, please read the full text of the
  [GNU General Public License]
  (https://www.gnu.org/licenses/gpl-3.0.html).

## Additional Information:
- If you modify this program and distribute it, you must include a copy of
  this license.
- Please contribute your improvements back to the community when possible.

Thank you for choosing our software and supporting open-source development!
"""))


class _Parser:
    COMMAND_NAME = set(string.ascii_letters + ".")
    INTEGER = set("0123456789-+")
    DECIMAL = set("0123456789.")
    NUMBER = INTEGER | DECIMAL
    Next = tuple[str | type(None), int]

    class WrongLiteral(Exception):
        params: tuple[str, str, int, int, int]

        @annotate
        def __init__(
            self, msg: str, text: str, begin: int, pos: int, end: int
        ):
            self.params = (msg, text, begin, pos, end)

    @classmethod
    @annotate
    def next_command_name(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        pos = begin
        if len(text) == pos:
            return None, pos
        while len(text) > pos and text[pos] in cls.COMMAND_NAME:
            pos += 1
        return text[begin:pos], pos

    @classmethod
    @annotate
    def next_literal(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        pos = begin
        if len(text) == pos:
            return None, pos
        for k in ("True", "False", "Nil", "None"):
            if text[pos:].startswith(k):
                return k, pos + len(k)
        if text[pos] in cls.NUMBER:
            return cls.next_number(text, pos)
        else:
            return None, begin

    @classmethod
    @annotate
    def next_key(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        pos = begin
        if len(text) == pos or text[pos] != "-":
            return None, pos
        if len(text) > pos + 1 and text[pos + 1].isdigit():
            return None, begin
        while len(text) > pos and not text[pos].isspace():
            pos += 1
        return text[begin:pos], pos

    @classmethod
    @annotate
    def next_number(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        pos = begin
        if len(text) == pos:
            return None, pos
        while len(text) > pos and not text[pos].isspace():
            pos += 1
        num = text[begin:pos]
        if len(d := (set(num) - cls.NUMBER)) > 0:
            raise cls.WrongLiteral(
                "wrong number literal",
                text,
                begin,
                min(text.index(t) for t in d),
                pos,
            )
        else:
            return text[begin:pos], pos


@annotate
class S_Interpreter:
    scope: S_NameSpace
    shell: Shell

    def __init__(self):
        self.shell = Shellsy()
        self.stacktrace = StackTrace()

    def eval(self, line: str):
        self.stacktrace.clear()
        command = self.parse_line(line)
        if isinstance(command, S_Command):
            return command.evaluate()
        else:
            return command

    def parse_line(self, line: str):
        # can be comment or shellsy command
        if line.strip().startswith("#"):  # comment, we pass
            return None
        else:  # shellsy command
            return self.parse_command(line)

    def parse_command(self, call: str):
        pos = 0
        cmd_name, end = _Parser.next_command_name(call, pos)
        self.stacktrace.add(pos, end, 0, call, "<command>")
        command = self.get_command(cmd_name)
        self.stacktrace.pop()
        pos = end

        arguments = self.parse_arguments(call, pos)

        return command, arguments

    def get_command(self, name: str):
        return Command()

    def parse_arguments(self, string: str, pos: int = 0):
        if string[pos:].strip() == "":
            return S_Arguments([], {}, "")
        else:
            args = []
            kwargs = {}
            last_key = None
            while pos < len(string):
                self.stacktrace.add(
                    pos + 1, len(string), 0, string, "<argument>"
                )
                lit, idx = _Parser.next_key(string, pos)  # try get a key
                if lit is not None:  # found key
                    last_key = (lit, idx - len(lit))
                    kwargs[last_key] = (Nil, None)
                else:
                    try:
                        lit, idx = _Parser.next_literal(string, pos)
                    except _Parser.WrongLiteral as wl:
                        msg, text, begin, pos, end = wl.params
                        self.stacktrace.add(pos, end, 0, text, "<literal>")
                        raise ShellsyException(
                            msg,
                            self.stacktrace,
                        )
                    else:
                        if lit is None:
                            raise ShellsyException(
                                "Unrecognised literal", self.stacktrace
                            )
                        val = self.evaluate_literal(lit)
                        v = (val, (idx - len(lit), lit))
                        if last_key is not None:
                            kwargs[last_key] = v
                        else:
                            args.append(v)
                pos = idx
                self.stacktrace.pop()
            return S_Arguments(args, kwargs, string)

    @annotate
    def evaluate_literal(
        self, string: str, pos=1, full_string=None
    ) -> S_Object:
        string_set = set(string)

        if string == "True":
            return S_bool(True)
        elif string == "False":
            return S_bool(False)
        elif string == "Nil":
            return Nil
        elif string == "None":
            return None
        elif len(string_set - _Parser.INTEGER) == 0:
            return S_int(string)


inter = S_Interpreter()

try:
    print(inter.eval("7"))
except ShellsyException as e:
    e.show()
