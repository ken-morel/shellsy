import os

from .exceptions import *
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from pyoload import *
from typing import Iterable
from typing import Optional


class Context(dict):
    pass


context = Context(
    {
        "_": None,
        "out": [],
    }
)


class ShellsyCustomType:
    pass


class NilType(ShellsyCustomType):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NilType, cls).__new__(cls)
        return cls._instance

    def __repr__(self):
        return "Nil"

    def __reduce__(self):
        return (NilType, ())

    def __bool__(self):
        return False


class _WordsMeta(type):
    """Metaclass for creating Keyword subclasses dynamically."""

    def __getitem__(cls, items):
        from typing import Union

        if not isinstance(items, tuple):
            items = (items,)
        for w in items:
            if w not in Word.words:
                Word.add(w)
        return Union[tuple(map(Word.words.get, items))]


class Word(ShellsyCustomType, metaclass=_WordsMeta):
    class DoesNotExist(ShellsyNtaxError, ValueError):
        pass

    words = {}

    def __reduce__(self):
        return self._name

    def __new__(cls, name, *args, **kwargs):
        if name in cls.words:
            return cls.words[name]()
            # return super(Word, cls).__new__(cls.keywords[name])
        else:
            raise Word.DoesNotExist(name)

    @classmethod
    def add(cls, name):
        setattr(
            Word,
            name,
            new_class := type(
                "Word." + name,
                (Word._Word, cls),
                {
                    "name": name,
                },
            ),
        )
        cls.words[name] = new_class
        return super(Word, cls).__new__(new_class)

    def __instancecheck__(self, obj):
        if isinstance(obj, str):
            obj = Word(obj)
        if object.__instancecheck__(obj):
            return obj.name == self.name
        return False

    def __repr__(self):
        return f"{self.name}"

    def __hash__(self):
        return hash(self.name)

    class _Word:
        _instance = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = object.__new__(cls)
            return cls._instance


class CommandBlock(ShellsyCustomType):
    commands: Iterable[str]
    auto_evaluate = False

    def __init__(self, commands: Iterable[str], auto_evaluate=False):
        from .args import CommandCall

        self.auto_evaluate = auto_evaluate
        self.commands = list(map(CommandCall.from_string, commands))

    def evaluate(self, shell=None):
        from .shell import Shell

        ret = None

        for cmd in self.commands:
            ret = (shell or Shell.master).call(cmd)

        return ret

    @classmethod
    def from_string(cls, string):
        auto_evaluate = (
            len(string) > 1 and string[0] == "{" and string[-1] == "}"
        )
        if auto_evaluate:
            string = string[1:-1]
        print(auto_evaluate)
        lines = []
        pos = 0
        while pos < len(string):  # collect each line
            stack = []
            begin = pos
            while pos < len(string):
                if string[pos] == "{":
                    stack.append("{")
                elif string[pos] == "}":
                    stack.pop()
                elif string[pos] == ";" and len(stack) == 0:
                    # pos += 1
                    break
                pos += 1
            lines.append(string[begin:pos].strip())
            pos += 1
        return cls(lines, auto_evaluate=auto_evaluate)

    def __repr__(self):
        return "{" + ";".join(map(str, self.commands)) + "}"


@annotate
class Expression(ShellsyCustomType):
    evaluators = {}
    type: str
    string: str
    context: "Context"
    auto_evaluate = False

    def __init__(self, type: str, string: str, context: Context = context, fullstring=None):
        self.type = type
        self.string = string
        if len(string) > 1 and string[0] == "(" and string[-1] == ")":
            self.auto_evaluate = True
            string = string[1:-1]
        self.context = context
        if type not in Expression.evaluators:
            STACKTRACE.add(Stack(
                content=type,
                parent_text=fullstring or string,
                parent_pos=(1, (fullstring or string).find(type)),
                file="<expr>"
            ))
            raise ShellsyNtaxError(
                f"Unrecognised expression type {type!r}",
            )

    def __call__(self):
        return Expression.evaluate(self.type, self.string, self.context)

    @classmethod
    def evaluate(cls, type, string, context):
        if type not in cls.evaluators:
            raise ShellsyNtaxError(
                f"Unrecognised expression prefix {type!r}",
                ("<string>", 1, 1, type, 1, len(type)),
            )
        return cls.evaluators[type](context, string).evaluate()

    def __repr__(self):
        return f"({self.type}#{self.string})"

    class Evaluator:
        def __init_subclass__(cls):
            Expression.evaluators[cls.prefix] = cls

        def __init__(self, context, string):
            self.string = string
            self.context = context

        def evaluate(self):
            raise NotImplementedError("should be overriden in subclasses")


class PythonEvaluator(Expression.Evaluator):
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
                STACKTRACE.add(
                    Stack(
                        content=fulltext[begin - 1:begin + le],
                        parent_pos=(lineno, begin),
                        parent_text=fulltext,
                        file=file,
                    )
                )
            raise ShellsyNtaxError(str(e))
        except Exception as e:
            print(e)


class Point(tuple, ShellsyCustomType):
    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    @property
    def z(self):
        return self[2]

    def __repr__(self):
        return f"Point{tuple.__repr__(self)}"


Nil = NilType()

Literal = (
    int
    | Decimal
    | Path
    | str
    | slice
    | list
    | dict
    | ShellsyCustomType
    | type(None)
    | bool
    | type(Nil)
)


@annotate
class Variable(ShellsyCustomType):
    name: str
    context: Context
    auto_evaluate = False

    def __init__(self, name: str, context: Context = context):
        self.name = name
        self.context = context

    def __call__(self, val: Literal = None) -> Literal:
        if val is not None:
            self.context[self.name] = val
        return self.context.get(self.name)

    def __repr__(self):
        return f"${self.name}"  # :{self.context.get(self.name)!r}


class ArgumentTypeMismatch(TypeError):
    def __init__(self, param, val, pos=-1):
        self.param = param
        self.val = val
        self.pos = pos

    def show(self):
        msg = (
            f"Value {self.val!r} does not match spec of parameter {self.param}"
        )
        if self.pos > -1:
            msg += f"(Positional argument {self.pos})"
        print(msg)


@annotate
def evaluate_literal(string: str, pos=1, full_string=None) -> Literal:
    digits = set("01234567890e-E")
    decimals = digits | set(".")
    string_quotes = set("'\"")
    string_set = set(string)
    slice_set = digits | set(":")
    point_set = digits | set(",.")

    if string == "True":
        STACKTRACE.pop()
        return True
    elif string == "False":
        return False
    elif string == "Nil":
        return Nil
    elif string == "None":
        return None
    elif string in Word.words:
        return Word(string)
    elif string[0] == "$":
        return Variable(string[1:])
    elif len(string_set - digits) == 0:
        return int(string)
    elif len(string_set - decimals) == 0:
        return Decimal(string)
    elif string[0] in string_quotes:
        if string[0] != string[-1]:
            STACKTRACE.add(
                Stack(
                    content=string,
                    parent_pos=(1, pos + len(string) - 1),
                    parent_text=full_string or string,
                    file="<string>",
                )
            )
            raise ShellsyNtaxError(
                f"unterminated string literal:{string!r}",
                STACKTRACE,
            )
        return str(string[1:-1])
    elif string[0] == string[-1] == "/":
        return Path(os.path.expandvars(string[1:-1]))
    elif string[0] == "[" and string[-1] == "]":
        if string == "[]":
            return []
        elif string == "[-]":
            return {}
        args = Arguments.from_string(string[1:-1])
        if len(args.kwargs) == 0:
            return args.args
        else:
            return args.kwargs
    elif ":" in string and len(string_set - slice_set) == 0:
        if len(string_set - slice_set) == 0:
            return slice(*map(int, string.split(":")))
        err = tuple(string_set - slice_set)
        cpos = string.index(err[0]) + 1
        STACKTRACE.add(
            Stack(
                content=string,
                parent_pos=(1, cpos + pos),
                parent_text=full_string or string,
                file="<argument>",
            )
        )
        raise ShellsyNtaxError(
            f"unknown characters {err}" f"in string {string!r}",
            STACKTRACE,
        )
    elif len(string_set - point_set) == 0:
        return Point(
            map(lambda x: float(x) if "." in x else int(x), string.split(","))
        )
    elif len(string) >= 2 and string[0] == "(" and string[-1] == ")":
        if "#" in string:
            if string[1: (idx := string.index("#"))].isalpha():
                return Expression(string[1:idx], string[idx + 1 : -1], fullstring=string)
            elif string[2: (idx := string.index("#"))].isalpha():
                return Expression(string[2:idx], string[idx + 1 : -1], fullstring=string)
        return Expression("py", string[1:-1], fullstring=string)
    elif len(string) >= 2 and string[0] == "{" and string[-1] == "}":
        return CommandBlock.from_string(string[1:-1])
    else:
        STACKTRACE.add(
            Stack(
                content=string,
                parent_pos=(1, pos),
                parent_text=full_string,
                file="<arguments>",
            )
        )
        raise ShellsyNtaxError(
            f"unrecognised literal:{string!r}",
        )


@dataclass
class Arguments:
    args: list
    kwargs: dict[str]
    full_string: str
    kwmaps: dict
    argmaps: list

    def __str__(self):
        return f"({self.args}, {self.kwargs})"

    @classmethod
    @annotate
    def from_string(cls, string: str):
        pos = 0
        string_parts = []
        # split string
        while pos < len(string):
            STACKTRACE.add(
                Stack(
                    content=string[pos:],
                    parent_pos=(1, pos),
                    parent_text=string,
                    file="<call>",
                )
            )
            if string[pos] in ("'\""):
                quote = string[pos]
                text = quote
                pos += 1
                while pos < len(string):
                    if string[pos] == "\\":
                        if len(string) == pos + 1:
                            STACKTRACE.add(
                                Stack(
                                    content=string[pos:],
                                    parent_pos=(1, pos),
                                    parent_text=string,
                                    file="<string>",
                                )
                            )
                            raise ShellsyNtaxError(
                                f"Escaped nothing at end of string:{string!r}",
                                STACKTRACE,
                            )
                        elif string[pos + 1] in ("'\"\\"):
                            text += string[pos + 1]
                            pos += 2
                        else:
                            STACKTRACE.add(
                                Stack(
                                    content=string[pos : pos + 2],
                                    parent_pos=(1, pos),
                                    parent_text=string,
                                    file="<string>",
                                )
                            )
                            raise ShellsyNtaxError(
                                (
                                    f"unknown escape {string[pos:pos+2]!r} in"
                                    f" {string!r}"
                                ),
                                STACKTRACE,
                            )
                    elif string[pos] == quote:
                        pos += 1
                        break
                    else:
                        text += string[pos]
                        pos += 1
                        if pos >= len(string):
                            STACKTRACE.add(
                                Stack(
                                    content=string[pos - 1:],
                                    parent_pos=(1, pos - 1),
                                    parent_text=string,
                                    file="<string>",
                                )
                            )
                            raise ShellsyNtaxError(
                                (f"unterminated string literal"),
                                STACKTRACE,
                            )
                string_parts.append((pos - len(text), text + quote))
            elif string[pos] == "/":
                begin = pos
                pos += 1
                while pos < len(string) and not (
                    string[pos] == "/"
                    and (len(string) == pos + 1 or string[pos + 1].isspace())
                ):
                    pos += 1
                string_parts.append((begin, string[begin : pos + 1]))
            elif string[pos] == "(":
                chars = ("(", ")")
                begin = pos
                pos += 1
                stack = []
                while pos < len(string):
                    if string[pos] == ")" and len(stack) == 0:
                        break
                    elif string[pos] in chars[0]:
                        stack.append(string[pos])
                    elif string[pos] in chars[1]:
                        stack.pop()
                    pos += 1
                string_parts.append((begin, string[begin : pos + 1]))
            elif string[pos] == "{":
                chars = ("{", "}")
                begin = pos
                pos += 1
                stack = []
                while pos < len(string):
                    if string[pos] == "}" and len(stack) == 0:
                        break
                    elif string[pos] in chars[0]:
                        stack.append(string[pos])
                    elif string[pos] in chars[1]:
                        stack.pop()
                    pos += 1
                string_parts.append((begin, string[begin : pos + 1]))
            elif string[pos] == "[":
                chars = ("[", "]")
                begin = pos
                pos += 1
                stack = []
                while pos < len(string):
                    if string[pos] == "]" and len(stack) == 0:
                        break
                    elif string[pos] in chars[0]:
                        stack.append(string[pos])
                    elif string[pos] in chars[1]:
                        stack.pop()
                    pos += 1
                string_parts.append((begin, string[begin : pos + 1]))
            elif not string[pos].isspace():
                begin = pos
                while len(string) > pos and not string[pos].isspace():
                    pos += 1
                string_parts.append((begin, string[begin:pos]))
            pos += 1
            STACKTRACE.pop()
        del pos
        return cls.from_string_parts(
            [(i, s) for i, s in string_parts if s], string=string
        )

    @classmethod
    @annotate
    def from_string_parts(
        cls,
        string_parts: Iterable[str | tuple[int, str, str]],
        string=None,
    ):
        args = []
        kwargs = {}

        string_parts = [
            (1, s) if isinstance(s, str) else s for s in string_parts
        ]

        def is_key(string):
            return string[0] == "-" and len(string) > 1 and string[1].isalpha()

        for idx, (_, ch) in string_parts[:]:
            if ch == "#":
                string_parts = string_parts[idx:]

        idx = 0
        while idx < len(string_parts):
            pos, part = string_parts[idx]
            if is_key(part):
                key = part[1:]
                val = "Nil"
                if idx + 1 < len(string_parts) and not is_key(
                    string_parts[idx + 1][1]
                ):
                    pos, val = string_parts[idx + 1]
                    idx += 1
                kwargs[key] = (pos, val)
            else:
                args.append((pos, part))
            idx += 1
        # evaluate literals
        argmaps = [
            (pos, val)  # TODO: maybe simplify this if extra info not needed
            for pos, val in args
        ]
        args = [
            evaluate_literal(val, pos=pos, full_string=string)
            for pos, val in args
        ]
        kwmaps = {key: (pos, val) for key, (pos, val) in kwargs.items()}
        kwargs = {
            key: evaluate_literal(val, pos=pos, full_string=string)
            for key, (pos, val) in kwargs.items()
        }
        return Arguments(
            args, kwargs, full_string=string, kwmaps=kwmaps, argmaps=argmaps
        )
