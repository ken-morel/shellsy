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

from decimal import Decimal
from pathlib import Path
from pyoload import type_match
import string

from pyoload import annotate


class S_Object:
    __slots__ = ()


class S_Point(S_Object, tuple):
    pass


class S_NameSpace(S_Object, dict):
    __slots__ = S_Object.__slots__


class S_Command(S_Object):
    command: "Command"
    arguments: "CommandArguments"

    def __init__(self, command: "Command", args: "S_Arguments"):
        self.command = command
        self.args = args

    def evaluate(self):
        return self.command(self.args)


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


S_Literal = (
    int
    | Decimal
    | Path
    | str
    | slice
    | list
    | dict
    | S_Object
    | type(None)
    | bool
    | NilType
)


class _Word_meta(type):
    def __getitem__(self, items):
        if isinstance(items, str):
            items = (items,)
        return tuple(map(Word, items))


class Word(S_Object, metaclass=_Word_meta):
    _instances = {}

    def __new__(cls, name: str):
        if name not in cls._instances:
            cls._instances[name] = super().__new__(cls)
            cls._instances[name].name = name
        return cls._instances[name]

    def __repr__(self):
        return self.name

    def __reduce__(self):
        return (self.__class__, ())

    def __instancecheck__(self, other):
        return other is self

    def __hash__(self):
        return hash(self.name)


class S_Variable(S_Object, str):
    def __repr__(self):
        return "$" + self


class S_Expression(S_Object):
    evaluators = {}
    type: str
    string: str
    auto_evaluate = False

    def __init__(
        self,
        type: str,
        string: str,
        fullstring=None,
        idx=0,
    ):
        self.type = type
        self.string = string
        if len(string) > 1 and string[0] == "(" and string[-1] == ")":
            self.auto_evaluate = True
            string = string[1:-1]
        if type not in S_Expression.evaluators:
            raise WrongLiteral(
                f"Unrecognised expression type {type!r}",
                fullstring,
                idx,
                string,
            )

    def __repr__(self):
        return f"({self.type}#{self.string})"

    class Evaluator:
        def __init_subclass__(cls):
            S_Expression.evaluators[cls.prefix] = cls

        def __init__(self, context, string):
            self.string = string
            self.context = context

        def evaluate(self):
            raise NotImplementedError("should be overriden in subclasses")


class PythonEvaluator(S_Expression.Evaluator):
    prefix = "py"

    def evaluate(self):
        import __main__
        import shellsy.shell

        try:
            return (exec if self.string.endswith(";") else eval)(
                self.string, self.context, vars(__main__) | vars(shellsy.shell)
            )
        except SyntaxError as e:
            try:
                file, lineno, begin, fulltext, _, le = e.args
            except Exception:
                _, (file, lineno, begin, fulltext, __, le) = e.args
            finally:
                # STACKTRACE.add(
                #     Stack(
                #         content=fulltext[begin - 1 : begin + le],
                #         parent_pos=(lineno, begin - 1),
                #         parent_text=fulltext,
                #         file=file,
                #     )
                # )
                raise ShellsyNtaxError(str(e))
        except Exception as e:
            print(e)


class _Parser:
    COMMAND_NAME = set(string.ascii_letters + ".")
    INTEGER = set("0123456789-+")
    DECIMAL = INTEGER | set(".")
    NUMBER = INTEGER | DECIMAL
    SLICE = INTEGER | set(":")
    STRING_QUOTES = set("\"'`")
    POINT = DECIMAL | set(",")
    VAR_NAME = set(string.ascii_letters + "01234567890_")
    Next = tuple[str | type(None), int]

    class WrongLiteral(Exception):
        params: tuple[str, str, int, int, int]

        def __init__(self, msg: str, text: str, begin: int, pos: int, end: int):
            self.params = (msg, text, begin, pos, end)

    @classmethod
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
        elif text[pos] in cls.STRING_QUOTES:
            return cls.next_string(text, pos)
        elif text[pos] == "[":
            k, end = cls.next_dict(text, pos)
            if k is not None:
                return k, end
            else:
                return cls.next_list(text, pos)
        elif text[pos] == "/":
            return cls.next_path(text, pos)
        elif text[pos] == "$":
            return cls.next_varname(text, pos)
        else:
            return None, begin

    @classmethod
    def next_key(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        pos = begin
        if len(text) == pos or text[pos] != "-":
            return None, pos
        if len(text) > pos + 1 and text[pos + 1].isdigit():
            return None, begin
        pos += 1
        while text[pos] in cls.VAR_NAME:
            pos += 1
            if len(text) == pos:
                return text[begin:pos], pos - 1
        return text[begin:pos], pos

    @classmethod
    def next_string(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        if len(text) == begin or text[begin] not in cls.STRING_QUOTES:
            return None, begin
        pos = begin + 1
        while text[pos] != text[begin]:
            if text[pos] == "\\":
                pos += 2
            else:
                pos += 1
            if pos >= len(text):
                raise cls.WrongLiteral(
                    "unterminated string literal",
                    text,
                    begin,
                    begin + 1,
                    len(text),
                )
        return text[begin : pos + 1], pos + 1

    @classmethod
    def next_number(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        pos = begin
        if len(text) == pos:
            return None, pos
        for pos in range(pos, len(text)):
            if text[pos] not in cls.NUMBER:
                break
        else:
            pos += 1
        return text[begin:pos], pos

    @classmethod
    def next_varname(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        if len(text) == begin or text[begin] != "$":
            return None, begin
        pos = begin + 1
        while pos < len(text) and text[pos] in cls.VAR_NAME:
            pos += 1
        return text[begin : pos + 1], pos + 1

    @classmethod
    def next_list(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        if len(text) == begin or text[begin] != "[":
            return None, begin
        pos = begin + 1
        while text[pos] != "]":
            _, end = cls.next_literal(text, pos)
            if end >= len(text):
                raise cls.WrongLiteral(
                    "Unterminated list",
                    text,
                    begin,
                    len(text) - 1,
                    len(text),
                )
            pos = end
        return text[begin : pos + 1], pos + 1

    @classmethod
    def next_dict(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        if len(text) == begin or text[begin : begin + 2] != "[-":
            return None, begin
        if text[begin : begin + 3] == "[-]":
            return "[-]", begin + 3
        pos = begin + 1
        while text[pos] != "]":
            k, end = cls.next_key(text, pos)
            if k is None:
                k, end = cls.next_literal(text, pos)
            if k is None:
                raise cls.WrongLiteral(
                    "Wrong key",
                    text,
                    begin,
                    pos,
                    pos + 1,
                )
            pos = end
            while len(text) > pos and text[pos].isspace():
                pos += 1
            if pos >= len(text):
                raise cls.WrongLiteral(
                    "Unterminated dict",
                    text,
                    begin,
                    pos,
                    pos + 1,
                )
        return text[begin : pos + 1], pos + 1

    @classmethod
    def next_path(cls, text: str, begin: int = 0) -> Next:
        while len(text) > begin and text[begin].isspace():
            begin += 1
        if len(text) == begin or text[begin] != "/":
            return None, begin
        pos = begin
        while pos < len(text):
            pos = text.find("/", pos + 1)
            if pos < 0:
                pos += len(text)
            elif pos == len(text) - 1 or text[pos + 1] == " ":
                break

        else:
            raise cls.WrongLiteral(
                "Unterminated path",
                text,
                begin,
                pos,
                pos + 1,
            )
        return text[begin : pos + 1], pos + 1
