import comberload
import os
from .args import *
from pyoload import *
from typing import Callable
from typing import Iterable
from .settings import *
from inspect import _empty
from rich import print


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

    @comberload("prompt_toolkit.completion")
    def nested_completer(self):
        from prompt_toolkit.completion import NestedCompleter

        completions = {x: None for x in self.get_possible_subcommands()}
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

        base_style = style_from_pygments_cls(get_style_by_name(get_setting("stylename", "monokai")))
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
            Literal,
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

            commands = [
                *[
                    (
                        r"(" + command.replace(".", "\\.") + "\\b)",
                        Name.Function,
                    )
                    for command in self.get_possible_subcommands()
                ],
                *[(f"\\b{c}\\b", Keyword) for c in ShellsyWord.words],
                (
                    r"^(\$)([\w_]+)\s*(\:)",
                    bygroups(Punctuation, Name.Variable, Keyword),
                ),
                (r"^([\w._]+)", Error),
                (r"True|False|Nil", Keyword),
                (
                    r"(\()(\w+)#(.*)(\))",
                    bygroups(
                        Punctuation, Keyword, String.Single, Punctuation
                    ),
                ),
                (
                    r"\(",
                    Punctuation, "python-expression",
                ),
                (
                    r"(?<!^)(\$)([\w_]+)",
                    bygroups(Punctuation, Name.Variable),
                ),
                # Double quoted strings (e.g., "arg1 string")
                (
                    r"(')([^']*)(')",
                    bygroups(Punctuation, String.Single, Punctuation),
                ),
                (
                    r'(")([^"]*)(")',
                    bygroups(Punctuation, String.Double, Punctuation),
                ),
                (
                    r"(-?[\d.]+)(\:)(-?[\d.]+)(\:)(-?[\d.]+)",
                    bygroups(
                        Literal.Number,
                        Punctuation,
                        Literal.Number,
                        Punctuation,
                        Literal.Number,
                    ),
                ),
                (
                    r"(-?[\d.]+)(\:)(-?[\d.]+)",
                    bygroups(Literal.Number, Punctuation, Literal.Number),
                ),
                (r"-?[\d.]+(?:,-?[\d.]+)+", Literal.Number),
                (r"-?\d+", Number),
                (r"-?[\d.]+", Literal.Number.Float),
                (r"(-)(\w+)", bygroups(Punctuation, Name.Label)),
                (r"/", Punctuation, "pathcontent"),
                (r"(?<!\s)\s(?!\s)", Generic),
            ]

            tokens = {
                "root": [
                    (r'^\s*#.+', Comment.Single),
                    (r"\{", Punctuation, "commandblock"),
                    *commands,
                ],
                "pathcontent": [
                    (r"\w\:", Name.Namespace),
                    (r"/(?=\w|\d|_|\-)", Operator),
                    (r"[\w\d_\-\s]+", Generic),
                    (r"\.[\w_\-]+(?=/)", Name.Namespace),
                    (r"/(?=\s|\b|$)", Punctuation, "#pop"),
                ],
                "commandblock": [
                    (r"\}", Punctuation, "#pop"),
                    (r";", Punctuation),
                    *commands,
                ],
                'python-expression': [
                    # (r'[^\(]+', Punctuation),
                    (r'\)', Punctuation, '#pop'),  # End of inline Python
                    include('python'),  # Include Python lexer rules
                ],
                'python': [
                    (r'\s+', Text),
                    (r'\\\n', Text),
                    (r'\\', Text),
                    (r'(print|exec|assert|lambda)\b', Keyword),
                    (r'(if|else|elif|while|for|try|except|finally|with|as|'
                     r'pass|break|continue|return|yield|raise|del|global|'
                     r'nonlocal|assert|True|False|None|and|or|not|is|in)\b', Keyword),
                    (r'(self|cls)\b', Name.Builtin.Pseudo),
                    (r'(Ellipsis|NotImplemented)\b', Name.Builtin.Pseudo),
                    (r'(abs|divmod|input|open|staticmethod|all|enumerate|int|ord|str|'
                     r'any|eval|isinstance|pow|sum|ascii|exec|issubclass|print|super|'
                     r'bin|filter|iter|property|tuple|bool|float|len|range|type|'
                     r'bytearray|format|list|repr|vars|bytes|frozenset|locals|'
                     r'reversed|zip|callable|getattr|map|round|__import__|chr|globals|'
                     r'max|set|complex|hasattr|memoryview|slice|delattr|hash|min|'
                     r'sorted|dict|help|next|staticmethod|dir|hex|object|str|'
                     r'enumerate|id|oct|sum|exec|input|open|property|type|print|'
                     r'staticmethod|sorted|super|vars|all|any|bin|bool|bytearray|'
                     r'bytes|callable|chr|classmethod|compile|complex|delattr|dict|'
                     r'dir|divmod|enumerate|eval|filter|float|format|frozenset|getattr|'
                     r'globals|hasattr|hash|help|hex|id|input|int|isinstance|'
                     r'issubclass|iter|len|list|locals|map|max|memoryview|min|next|'
                     r'object|oct|open|ord|pow|property|range|repr|reversed|round|'
                     r'set|setattr|slice|sorted|staticmethod|str|sum|super|tuple|type|'
                     r'vars|zip|__import__)\b', Name.Builtin),
                    (r'(True|False|None)\b', Name.Builtin.Pseudo),
                    (r'(int|long|float|complex)\b', Name.Builtin),
                    (r'(set|list|dict|tuple|frozenset)\b', Name.Builtin),
                    (r'(object|type)\b', Name.Builtin),
                    (r'(BaseException|Exception|ArithmeticError|BufferError|'
                     r'LookupError|AssertionError|AttributeError|EOFError|'
                     r'FloatingPointError|GeneratorExit|ImportError|ModuleNotFoundError|'
                     r'IndexError|KeyError|KeyboardInterrupt|MemoryError|NameError|'
                     r'NotImplementedError|OSError|OverflowError|RecursionError|'
                     r'ReferenceError|RuntimeError|StopIteration|StopAsyncIteration|'
                     r'SyntaxError|IndentationError|TabError|SystemError|SystemExit|'
                     r'TypeError|UnboundLocalError|UnicodeError|UnicodeEncodeError|'
                     r'UnicodeDecodeError|UnicodeTranslateError|ValueError|'
                     r'ZeroDivisionError)\b', Name.Builtin.Exception),
                    (r'(abs|all|any|ascii|bin|bool|bytearray|bytes|callable|chr|'
                     r'classmethod|compile|complex|delattr|dict|dir|divmod|enumerate|'
                     r'eval|exec|filter|float|format|frozenset|getattr|globals|'
                     r'hasattr|hash|help|hex|id|input|int|isinstance|issubclass|iter|'
                     r'len|list|locals|map|max|memoryview|min|next|object|oct|open|'
                     r'ord|pow|print|property|range|repr|reversed|round|set|setattr|'
                     r'slice|sorted|staticmethod|str|sum|super|tuple|type|vars|zip|'
                     r'__import__)\b', Name.Builtin),
                    (r'@\w+', Name.Decorator),
                    (r'@[A-Za-z_]\w*', Name.Decorator),
                    (r'(None|True|False|Ellipsis|NotImplemented)\b', Name.Builtin.Pseudo),
                    (r'(\d+\.\d*|\.\d+|\d+\.|\d+)([eE][+-]?\d+)?j?\b', Number.Float),
                    (r'0x[0-9a-fA-F]+', Number.Hex),
                    (r'0b[01]+', Number.Bin),
                    (r'0o[0-7]+', Number.Oct),
                    (r'\d+j?\b', Number.Integer),
                    (r'"(\\\\|\\"|[^"])*"', String.Double),
                    (r"'(\\\\|\\'|[^'])*'", String.Single),
                    (r'\\\n', String),
                    (r'\\', String),
                    (r'`.*?`', String.Backtick),
                    (r'\r\n|\n', Text),
                    (r'\r', Text),
                    (r'[\[\]{}:(),;]', Punctuation),
                    (r'==|!=|<=|>=|<<|>>|->|\+=|-=|\*=|/=|//=|%=|&=|\|=|^=|>>=|<<=|@=|\*\*|//|->|<<|>>|<>|!=|<=|>=|==|->|:|'
                     r'\+|-|\*|/|%|&|\||\^|~|<|>', Operator),
                    (r'(not|and|or)\b', Operator.Word),
                    (r'\.', Operator),
                    (r'=', Operator),
                    (r'\+\+|--|\*\*|//|\|\|', Operator),
                    (r'[*<>!&^~@|\-+=/%]', Operator),
                    (r'[()\[\]{}:.,;@]', Punctuation),
                    (r'\b(print|exec|assert|lambda|yield|return|import|from|class|def|'
                     r'elif|else|try|except|finally|raise|while|for|in|and|or|not|is|'
                     r'with|as|pass|break|continue|del|global|nonlocal|if|True|False|'
                     r'None)\b', Keyword),
                    (r'@[A-Za-z_]\w*', Name.Decorator),
                    (r'__\w+__', Name.Function.Magic),
                    (r'__\w+__', Name.Variable.Magic),
                    (r'__\w+__', Name.Class.Magic),
                    (r'__\w+__', Name.Constant.Magic),
                    (r'__[a-zA-Z_]\w*__', Name.Builtin.Pseudo),
                    (r'__[a-zA-Z_]\w*__', Name.Function.Magic),
                    (r'__[a-zA-Z_]\w*__', Name.Variable.Magic),
                    (r'__[a-zA-Z_]\w*__', Name.Class.Magic),
                    (r'__[a-zA-Z_]\w*__', Name.Constant.Magic),
                    (r'[a-zA-Z_]\w*', Name),
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
                    print(ret)
            except (
                NoSuchCommand,
                ArgumentTypeMismatch,
                ShellsyNtaxError,
            ) as e:
                e.show()
            # except Exception as e:
            #     print(e)
