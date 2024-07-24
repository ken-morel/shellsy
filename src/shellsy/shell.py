import comberload
import os
from .args import *
from pyoload import *
from typing import Callable
from typing import Iterable


class NoSuchCommand(ValueError):
    def show(self):
        print("No Such command")


class Command:
    params: CommandParameters

    def __init__(self, func: Callable):
        self.params = CommandParameters.from_function(func)
        self.__func__ = func

    @annotate
    def __call__(self, args: Arguments):
        args = self.params.bind(args)
        self.__func__(**args)

    def __set_name__(self, obj, name: str, typo=None):
        if not hasattr(obj, "commands"):
            obj.commands = {}
        self.name = name
        obj.commands[name] = self


@annotate
class Shell(Command):
    history = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "history.txt")
    )
    prompt_session = None
    _lexer = None
    _bindings = None

    def __init_subclass__(cls):
        cls.name = cls.__name__.lower()

    def __init__(self):
        if not hasattr(self, "subshells"):
            self.subshells = {}
        if not hasattr(self, "commands"):
            self.commands = {}

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
            print("exiting gracefully")
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

    @comberload("prompt_toolkit.completion")
    def nested_completer(self):
        from prompt_toolkit.completion import NestedCompleter

        completions = {
            "show": {
                "version": None,
                "clock": None,
                "ip": {"interface": {"brief"}},
            },
            "exit": None,
        }
        return NestedCompleter.from_nested_dict(completions)

    def format_cwd(self):
        import os
        from os import path

        cwd = os.getcwd()
        shortens = ("", "")
        for name, path in os.environ.items():
            if (
                cwd.startswith(path)
                and len(path) > len(name) + 2
                and len(path) > shortens[1]
            ):
                shortens = (name, path)
        if shortens[0]:
            return [
                ("class:envpath", "%" + shortens[1] + "%"),
                ("class:cwdpath", cwd[len(shortens[1]) :]),
            ]
        else:
            drive, path = os.path.splitdrive(cwd)
            return [("class:drivename", drive), ("class:cwdpath", path)]

    def get_styles(self):
        from prompt_toolkit.styles import Style
        return Style.from_dict(
            {
                # "": "#ffffff",
                "shellname": "#884444",
                "envpath": "#88ffaa",
                "drivename": "#0077ff",
                "cwdpath": "#ffff45",
                "prompt": "#00aa00",
                "path": "ansicyan underline",
                'pygments.keyword': 'underline',
                'pygments.name.function': 'underline reverse',
                'pygments.literal.string': '#ffff00',
                'pygments.punctuation': '#ff0000',
                'pygments.error': 'bg:#ff0000 underline',
            }
        )

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
            enable_history_search=True,
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
            completer=self.nested_completer(),
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
        import re
        from prompt_toolkit.lexers import PygmentsLexer
        from pygments.lexer import (
            # Lexer,
            RegexLexer,
            # do_insertions,
            include,
            # default,
            # this,
            # using,
            # words,
            # line_re,
            bygroups,
        )
        from pygments.token import (
            Punctuation,
            # Whitespace,
            Text,
            Comment,
            Operator,
            Keyword,
            Name,
            String,
            Number,
            Generic,
            Error,
        )

        class CustomLexer(RegexLexer):
            name = self.name
            aliases = [""]
            filenames = ["*.shellsy"]
            mimetypes = ["text/x-shellsy"]
            url = "https://github.com/ken-morel/shellsy"
            version_added = "0.0.1"
            flags = re.DOTALL | re.IGNORECASE | re.MULTILINE
            keywords = self.commands.keys()

            operators = []

            verbs = [""]

            aliases_ = []

            commenthelp = ["help"]

            tokens = {
                "root": [
                    *[
                        (
                            "^(" + command.replace(".", "\\.") + "\\b)",
                            Name.Function,
                        )
                        for command in self.get_possible_subcommands()
                    ],
                    (r"^([\w._]+)", Error),
                    # Double quoted strings (e.g., "arg1 string")
                    (r'"[^"]*"', String.Double),
                    # Single quoted strings (e.g., 'arg1 string')
                    (r"'[^']*'", String.Single),
                    # Numbers (e.g., 123)
                    (r"(\d+)", Number),
                    (r"(\d+x\d+)", Number),
                    (r"(/)", Punctuation, 'pathcontent'),
                    (r"(?<!\s)\s(?!\s)", Generic),
                ],
                'pathcontent': [
                    (r"\w\:", Name.Namespace),
                    (r"(/)(?=\w|\d|_|\-)", Operator),
                    (r"[\w\d_\-\s]+", Generic),
                    (r"\.[\w_\-]+(?=/)", Name.Namespace),
                    (r"(/)(?=\s|\b|$)", Punctuation, "#pop"),
                ]
            }

        self._lexer = PygmentsLexer(CustomLexer)
        return self._lexer

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
    def __call__(self, args: str | Iterable[str]):
        if isinstance(args, str):
            args = CommandCall.from_string(args)
        else:
            args = CommandCall.from_string_parts(args)
        if args.command:
            self.call(args)
        else:
            self.cmdloop()

    def call(self, call: CommandCall):
        name, inner = call.inner()
        if name in self.commands:
            return self.commands[name](inner.arguments)
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
                call = CommandCall.from_string(text)
                self.call(call)
            except (NoSuchCommand, ArgumentTypeMismatch) as e:
                e.show()
            # except Exception as e:
            #     print(e)

    def __set_name__(self, obj, name: str, typo=None):
        if not hasattr(obj, "subshells"):
            obj.subshells = {}
        self.name = name
        obj.subshells[name] = self
