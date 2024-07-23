import comberload

from .args import Parameters
from .args import group
from pathlib import Path
from pyoload import *
from typing import Callable
from typing import Iterable


class Command:
    params: Parameters

    # @annotate
    def __init__(self, *params):
        self.params = Parameters(*params)

    @annotate
    def __call__(self, func: Callable):
        self.__func__ = func
        return self

    @annotate
    def entrypoint(self, args: Iterable[str]):
        if isinstance(args, str):
            args = group(args)
        args = self.paramaters(args)
        self.__func__(args)

    def __set_name__(self, obj, name: str, typo=None):
        if not hasattr(obj, "commands"):
            obj.commands = {}
        self.name = name
        obj.commands[name] = self


@annotate
class Shell(Command):
    history = Path("./history.txt")
    prompt_session = None

    def __init_subclass__(cls):
        cls.name = cls.__name__.lower()

    @comberload("prompt_toolkit")
    def get_input(self):
        import prompt_toolkit

        if self.prompt_session is None:
            self.prompt_session = prompt_toolkit.PromptSession(
                validate_while_typing=True,
                bottom_toolbar=self.bottom_toolbar,
                rprompt=self.right_prompt,
                enable_history_search=True,
                history=self.history,
                lexer=self.lexer(),
                message=self.name + "\n> ",
            )
        return self.prompt_session.prompt()

    @get_input.fallback
    def raw_get_input(self):
        print("main")
        return input(self.name + "> ")

    @comberload(["pygments.lexer", "pygments.token"])
    def lexer(self):
        if self._lexer:
            return self._lexer
        import re

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
            # Number,
            # Generic,
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
                    (r"\(", Punctuation, "child"),
                    (r"\s+", Text),
                    (
                        r"^(\s*#[#\s]*)(\.(?:{}))([^\n]*$)".format(
                            "|".join(commenthelp)
                        ),
                        bygroups(Comment, String.Doc, Comment),
                    ),
                    (r"#[^\n]*?$", Comment),
                    (r"(&lt;|<)#", Comment.Multiline, "multline"),
                    # escaped syntax
                    (r'`[\'"$@-]', Punctuation),
                    (r'"', String.Double, "string"),
                    (r"'([^']|'')*'", String.Single),
                    (
                        r"(\$|@@|@)((global|script|private|env):)?\w+",
                        Name.Variable,
                    ),
                    (r"({})\b".format("|".join(keywords)), Keyword),
                    (r"-({})\b".format("|".join(operators)), Operator),
                    (
                        r"({})-[a-z_]\w*\b".format("|".join(verbs)),
                        Name.Builtin,
                    ),
                    (r"({})\s".format("|".join(aliases_)), Name.Builtin),
                    (
                        r"\[[a-z_\[][\w. `,\[\]]*\]",
                        Name.Constant,
                    ),  # .net [type]s
                    (r"-[a-z_]\w*", Name),
                    (r"\w+", Name),
                    (r"[.,;:@{}\[\]$()=+*/\\&%!~?^`|<>-]", Punctuation),
                ],
                "child": [
                    (r"\)", Punctuation, "#pop"),
                    include("root"),
                ],
                "multline": [
                    (r"[^#&.]+", Comment.Multiline),
                    (r"#(>|&gt;)", Comment.Multiline, "#pop"),
                    (r"\.({})".format("|".join(commenthelp)), String.Doc),
                    (r"[#&.]", Comment.Multiline),
                ],
                "string": [
                    (r"`[0abfnrtv'\"$`]", String.Escape),
                    (r'[^$`"]+', String.Double),
                    (r"\$\(", Punctuation, "child"),
                    (r'""', String.Double),
                    (r"[`$]", String.Double),
                    (r'"', String.Double, "#pop"),
                ],
                "heredoc-double": [
                    (r'\n"@', String.Heredoc, "#pop"),
                    (r"\$\(", Punctuation, "child"),
                    (r'[^@\n]+"]', String.Heredoc),
                    (r".", String.Heredoc),
                ],
            }

        self._lexer = CustomLexer()
        return self._lexer

    @lexer.fallback
    def _(self):
        return None

    def bottom_toolbar(self):
        return "bottom_toolbar"

    def right_prompt(self):
        return "rptompt"

    def entrypoint(self, args: str | Iterable[str]):
        if isinstance(args, str):
            args = group(args)
        if len(args) > 0:
            name, *args = args
            self.sub_call(name, args)
        else:
            self.cmdloop()

    def sub_call(self, name: str, args: Iterable[str]):
        if name in self.commands:
            return self.commands[name].entrypoint(args)
        else:
            raise ValueError("no such subcommand", name)

    def cmdloop(self):
        self.should_run = True
        while self.should_run:
            text = self.get_input()
            print(text)
            self.entrypoint(text)
