from . import lexer

import comberload
import os
from .args import *
from pyoload import *
from typing import Callable
from typing import Iterable
from .settings import *
from .help import CommandHelp
import time
from inspect import Signature
import logging
from rich.logging import RichHandler
from rich import print as pprint
from rich.markdown import Markdown

FORMAT = "%(message)s"

logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")


@annotate
class StatusText:
    __slots__ = ("text", "duration", "source", "begin")
    to_show = []
    shown = []
    showing = []
    cache_size = 50
    source: str
    text: str
    duration: int

    def __init__(self, text: str, duration: int, source: str):
        self.text = text
        self.duration = duration
        self.source = source
        StatusText.to_show.append(self)

    @classmethod
    def clear(cls):
        cls.shown.extend(cls.showing)
        cls.showing.clear()

    @classmethod
    def update(cls):
        for idx, stat in reversed(tuple(enumerate(cls.showing[:]))):
            if (time.perf_counter() - stat.begin) > stat.duration:
                cls.showing.pop(idx)
                cls.shown.append(stat)
                cls.shown = cls.shown[-cls.cache_size :]
            for ostat in cls.to_show:
                if ostat.source == stat.source:
                    cls.showing.pop(idx)
                    cls.shown.append(stat)
                    cls.shown = cls.shown[-cls.cache_size :]
        for stat in cls.to_show:
            stat.begin = time.perf_counter()
            cls.showing.append(stat)
        cls.to_show.clear()


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
    def __call__(self, shell, args: Arguments):
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
                    + "\n -".join(map(str, errors))
                )

    def __set_name__(self, cls, name):
        self.name = name

    def dispatch(self, func):
        self.dispatches.append(Command(func))


class Shell(Command):
    history = os.path.join(data_dir, "history.txt")
    prompt_session = None
    _lexer = None
    _bindings = None
    _log = ""

    def __init_subclass__(cls):
        cls.name = cls.__name__.lower()

    def __init__(self, parent=None):
        if parent:
            self.parent = parent
            self.master = parent.master
        else:
            self.parent = None
            self.master = self
        Shell.master = self.master
        if not hasattr(self, "subshells"):
            self.subshells = {}
        if not hasattr(self, "commands"):
            self.commands = {}

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
                    subcls.master = self.master
                    if attr[0] == "_":
                        attr = attr[1:]
                    self.subshells[attr] = subcls(parent=self)
            except (AttributeError, TypeError):
                pass

    @comberload(
        "prompt_toolkit.key_binding",
        "prompt_toolkit.application",
    )
    def key_bindings(self):
        if self._bindings is not None:
            return self._bindings

        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.application import run_in_terminal

        bindings = KeyBindings()

        @bindings.add("c-t")
        def _(event):
            "Say 'hello' when `c-t` is pressed."

            def print_hello():
                print("hello world")

            run_in_terminal(print_hello)

        @bindings.add("c-c")
        def _(event):
            "Exit when `c-x` is pressed."

            def print_hello():
                print("exiting gracefully!")

            run_in_terminal(print_hello)
            event.app.exit()

        @bindings.add("c-space")
        def _(event):
            "Initialize autocompletion, or select the next completion."
            buff = event.app.current_buffer
            if buff.complete_state:
                buff.complete_next()
            else:
                buff.start_completion(select_first=False)

        self._bindings = bindings
        return bindings

    def format_cwd(self):
        import os

        cwd = os.getcwd()
        shortens = ("", "")
        for name, path in os.environ.items():
            if (
                cwd.startswith(path)
                and len(path) > len(name) + 2
                and len(path) > len(shortens[1])
            ):
                shortens = (name, path)
        if shortens[0]:
            return [
                ("class:envpath", "%" + shortens[0] + "%"),
                ("class:cwdpath", cwd[len(shortens[1]) :]),
            ]
        else:
            drive, path = os.path.splitdrive(cwd)
            return [("class:drivename", drive), ("class:cwdpath", path)]

    @comberload("prompt_toolkit.styles", "pygments.styles")
    def get_styles(self):
        from prompt_toolkit.styles import Style
        from prompt_toolkit.styles import style_from_pygments_cls, merge_styles
        from pygments.styles import get_style_by_name

        base_style = style_from_pygments_cls(
            get_style_by_name(get_setting("stylename", "monokai"))
        )
        custom_style = Style.from_dict(
            {
                # "": "#ffffff",
                "shellname": "#884444",
                "envpath": "#88ffaa",
                "drivename": "#0077ff",
                "cwdpath": "#ffff45",
                "prompt": "#00aa00",
                "path": "ansicyan underline",
                "pygments.error": "bg:red",
                "pygments.punctuation": "red",
            }
        )
        return merge_styles([base_style, custom_style])

    @comberload(
        "prompt_toolkit",
        "prompt_toolkit.styles",
        "prompt_toolkit.history",
    )
    def get_input(self):
        import prompt_toolkit
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

        cwd = self.format_cwd()
        return prompt_toolkit.prompt(
            validate_while_typing=True,
            bottom_toolbar=self.bottom_toolbar,
            rprompt=self.right_prompt,
            # enable_history_search=True,
            history=FileHistory(self.history),
            lexer=self.lexer(),
            message=[
                *cwd,
                ("", "> "),
                ("class:shellname", self.name),
                ("", "\n"),
                ("class:prompt", "> "),
            ],
            style=self.get_styles(),
            completer=self.shell_completer(),
            auto_suggest=AutoSuggestFromHistory(),
            mouse_support=True,
            key_bindings=self.key_bindings(),
        )

    @get_input.failback
    def raw_get_input(self):
        return input(self.name + "> ")

    @comberload("pygments.lexer", "pygments.token")
    def lexer(self):
        if self.parent is not None:
            return self.parent.lexer()
        if self._lexer:
            return self._lexer

        self._lexer = lexer.for_shell(self)
        return self._lexer

    @comberload("prompt_toolkit.completion")
    def shell_completer(self):
        # TDOD: move this to another file and use cls(shell)
        from prompt_toolkit.completion import Completer, Completion

        def similarity(a, b):
            import difflib

            return difflib.SequenceMatcher(lambda *_: False, a, b).ratio()

        class ShellCompleter(Completer):
            def get_completions(_self, document, complete_event):
                # self.get_possible_subcommands()
                from string import ascii_letters
                from pathlib import Path

                line = document.current_line_before_cursor
                # yield Completion(line, start_position=0)
                comps = []
                if len(line) == 0:
                    return
                if (
                    line[0] == "$"
                    and len(set(line[1:]) - set(ascii_letters + "_")) == 0
                ):
                    for v in context:
                        v = "$" + v
                        comps.append((similarity(line[1:], v), v))
                    StatusText(
                        repr(context.get(line[1:])),
                        5,
                        source="__entry-var-values__",
                    )
                    comps.sort(key=lambda k: -k[0])
                    for _, x in comps:
                        yield Completion(x, start_position=-len(line))
                    return
                if (
                    " /" in line
                    and not line.endswith(" /")
                    and len(
                        set(line[line.rindex(" /") + 1 :])
                        - set(ascii_letters + "/\\ :-.")
                    )
                    == 0
                ):
                    *_, fpath = line.rsplit(" /", 1)
                    path, *_ = fpath.rsplit("/", 1)
                    all = Path(path)
                    if all.exists() and all.is_dir():
                        for sub in all.glob("*"):
                            comps.append(
                                (
                                    similarity(fpath, str(sub)[: len(fpath)]),
                                    str(sub),
                                    -len(fpath),
                                )
                            )
                    else:
                        for sword in tuple(Word.words.keys()) + (
                            "None",
                            "Nil",
                            "True",
                            "False",
                        ):
                            comps.append(
                                (
                                    similarity(line, sword[: len(line)]),
                                    sword,
                                    -len(line),
                                )
                            )
                if " " not in line:
                    for cmd in self.get_possible_subcommands():
                        cmd = cmd.replace(".__entrypoint__", "")
                        comps.append(
                            (
                                similarity(line, cmd[: len(line)]),
                                cmd,
                                -len(line),
                            )
                        )
                elif not line.endswith(" "):
                    _, cline = line.split(" ", 1)
                    if " " in cline and not cline.endswith(" "):
                        _, word = cline.rsplit(" ", 1)
                    else:
                        word = cline
                comps.sort(key=lambda c: -c[0] * 100)
                for _, comp, pos in comps:
                    yield Completion(comp, start_position=pos)

        return ShellCompleter()

    def get_possible_subcommands(self):
        possible = list(self.commands)
        for sub, val in self.subshells.items():
            possible.extend(
                [sub + "." + x for x in val.get_possible_subcommands()]
            )
        return possible

    def bottom_toolbar(self):
        try:
            StatusText.update()
        except Exception as e:
            return (
                str(e) + ";" + ";".join([x.text for x in StatusText.showing])
            )
        else:
            return ";".join([x.text for x in StatusText.showing])

    def right_prompt(self):
        return ""

    @annotate
    def __call__(self, args: str | Iterable[str] = ""):
        if isinstance(args, str):
            args = CommandCall.from_string(args)
        else:
            args = CommandCall.from_string_parts(args)
        if args is None:
            StatusText("could not parse that.")
            return
        if args.command:
            return self.call(args)
        else:
            if "__entrypoint__" in self.commands:
                return self.commands["__entrypoint__"](self, args.arguments)
            else:
                StatusText(self.__class__.__name__ + " has no entry point")
                return None

    @annotate
    def call(self, call: CommandCall):
        if not call.command:
            if "__entrypoint__" in self.commands:
                return self.commands["__entrypoint__"](self, call.arguments)
            else:
                raise NoSuchCommand(f"{self.name} has no entry point")
        name, inner = call.inner()
        if name in self.commands:
            return self.commands[name](self, inner.arguments)
        elif name in self.subshells:
            return self.subshells[name].call(inner)
        else:
            raise NoSuchCommand("no such subcommand: " + name)

    @annotate
    def get_command(self, cmd: str):
        call = CommandCall.from_string(cmd)
        if not call.command:
            if "__entrypoint__" in self.commands:
                return self.commands["__entrypoint__"]
            else:
                raise NoSuchCommand(f"{self.name} has no entry point")
        name, inner = call.inner()
        if name in self.commands:
            return self.commands[name]
        elif name in self.subshells:
            return self.subshells[name].get_command(inner.command)
        else:
            raise NoSuchCommand("no such subcommand to get", name)

    def cmdloop(self):
        try:
            intro = self.intro
        except AttributeError:
            pass
        else:
            pprint(Markdown(intro))
        self.should_run = True
        while self.should_run:
            STACKTRACE.clear()
            try:
                text = self.get_input()
                STACKTRACE.add(
                    Stack(
                        content=text or "",
                        parent_pos=(1, 0),
                        parent_text=None,
                        file="<cmd>",
                    )
                )
                if text is None:
                    break
                elif len(text) == 0 or text[0] == "#":
                    continue
                elif text[0] == "!":
                    import os

                    val = os.system(text[1:])
                else:
                    val = self(text)
                context["_"] = val
                context["out"].append(val)
                pprint(f"@{len(context['out']) - 1}>", val)
            except ShellsyError as e:
                e.show()

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
