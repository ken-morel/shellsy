import comberload
import os
from .args import *
from pyoload import *
from typing import Callable
from typing import Iterable
from .settings import *
from inspect import _empty
from rich.console import Console

console = Console()
pprint = console.print


class NoSuchCommand(ValueError):
    def show(self):
        print("No Such command")


class Command:
    params: CommandParameters

    def __init__(self, func: Callable):
        self.params = CommandParameters.from_function(func)
        self.__func__ = func

    @annotate
    def __call__(self, shell, args: Arguments):
        args = self.params.bind(args)
        return self.__func__(shell, **args)


class Shell(Command):
    history = os.path.join(data_dir, "history.txt")
    prompt_session = None
    _lexer = None
    _bindings = None
    console: Console = console

    def __init_subclass__(cls):
        cls.name = cls.__name__.lower()

    def __init__(self):
        if not hasattr(self, "subshells"):
            self.subshells = {}
        if not hasattr(self, "commands"):
            self.commands = {}

        for attr in dir(self):
            if attr.startswith("__"):
                continue
            try:
                if isinstance(cmd := getattr(self, attr), Command):
                    cmd.shell = self
                    if attr[0] == "_":
                        attr = attr[1:]
                    self.commands[attr] = cmd
                elif issubclass(subcls := getattr(self, attr), Shell):
                    subcls.shell = self
                    if attr[0] == "_":
                        attr = attr[1:]
                    self.subshells[attr] = subcls()
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
        from os import path

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

    @get_input.fallback
    def raw_get_input(self):
        return input(self.name + "> ")

    @comberload("pygments.lexer", "pygments.token")
    def lexer(self):
        if self._lexer:
            return self._lexer

        self._lexer = lexer.for_shell(self)
        return self._lexer

    def shell_completer(self):
        # TDOD: move this to another file and use cls(shell)
        from prompt_toolkit.completion import Completer, Completion
        import string

        def similarity(a, b):
            import difflib

            return difflib.SequenceMatcher(lambda *_: False, a, b).ratio()

        class ShellCompleter(Completer):
            def get_completions(_self, document, complete_event):
                # self.get_possible_subcommands()
                line = document.current_line_before_cursor
                # yield Completion(line, start_position=0)
                if " " not in line:
                    comps = []
                    for cmd in self.get_possible_subcommands():
                        comps.append((similarity(line, cmd[: len(line)]), cmd))
                    comps.sort(key=lambda c: -c[0] * 100)
                    for _, comp in comps:
                        yield Completion(comp, start_position=-len(line))
                elif not line.endswith(" "):
                    _, line = line.split(" ", 1)
                    if " " in line and not line.endswith(" "):
                        _, word = line.rsplit(" ", 1)
                    else:
                        word = line
                    comps = []
                    for sword in ShellsyWord.words + [
                        "None",
                        "Nil",
                        "True",
                        "False",
                    ]:
                        comps.append(
                            (similarity(line, sword[: len(line)]), sword)
                        )
                    comps.sort(key=lambda c: -c[0] * 100)
                    for _, comp in comps:
                        yield Completion(comp, start_position=-len(word))

        return ShellCompleter()

    def get_possible_subcommands(self):
        possible = list(self.commands)
        for sub, val in self.subshells.items():
            possible.extend(
                [sub + "." + x for x in val.get_possible_subcommands()]
            )
        return possible

    def bottom_toolbar(self):
        return "bottom_toolbar"

    def right_prompt(self):
        return "rptompt"

    @annotate
    def __call__(self, args: str | Iterable[str] = "", loop: bool = True):
        if isinstance(args, str):
            args = CommandCall.from_string(args)
        else:
            args = CommandCall.from_string_parts(args)
        if args.command:
            return self.call(args)
        elif loop:
            return self.cmdloop()
        else:
            return None

    @annotate
    def call(self, call: CommandCall):
        if not call.command:
            if hasattr(self, "__entrypoint__"):
                self.__entrypoint__(call.arguments)
            else:
                raise NoSuchCommand(f"{self.name} has no entry point")
        name, inner = call.inner()
        if name in self.commands:
            return self.commands[name](self, inner.arguments)
        elif name in self.subshells:
            return self.subshells[name].call(inner)
        else:
            raise NoSuchCommand("no such subcommand", name)

    def cmdloop(self):
        self.should_run = True
        while self.should_run:
            try:
                text = self.get_input()
                if text is None:
                    break
                else:
                    call = CommandCall.from_string(text)
                    ret = self.call(call)
                    pprint(ret)
            except (
                NoSuchCommand,
                ArgumentTypeMismatch,
                ShellsyNtaxError,
            ) as e:
                e.show()
            # except Exception as e:
            #     console.print_exception(show_locals=True)
            #     if input("continue? (y/n)> ").lower().startswith("y"):
            #         continue
            #     else:
            #         break
