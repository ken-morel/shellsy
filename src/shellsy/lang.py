import os
import comberload
from decimal import Decimal
from pathlib import Path
from pyoload import *
from typing import Iterable


class Context(dict):
    pass


context = Context()


class ShellsyNtaxError(SyntaxError):
    @comberload("prompt_toolkit")
    def show(self):
        from prompt_toolkit import print_formatted_text, HTML
        print(self)

    @show.failback
    def _show(self):
        print(self)


class ArgumentError(ShellsyNtaxError, ValueError):
    def show(self):
        print(self)


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


Word.add("as")  # representation
Word.add("else")  # for if
Word.add("in")  # membership


class CommandBlock(ShellsyCustomType):
    commands: Iterable[str]

    def __init__(self, commands: Iterable[str]):
        from .args import CommandCall

        self.commands = list(map(CommandCall.from_string, commands))

    def evaluate(self, shell):
        ret = None

        for cmd in self.commands:
            ret = shell.call(cmd)

        return ret

    @classmethod
    def from_string(cls, string):
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
        return cls(lines)

    def __repr__(self):
        return "<Commands{" + ";".join(map(str, self.commands)) + "}>"


@annotate
class Expression(ShellsyCustomType):
    evaluators = {}
    type: str
    string: str
    context: "Context"

    def __init__(self, type: str, string: str, context: Context = context):
        self.type = type
        self.string = string
        self.context = context
        if type not in Expression.evaluators:
            raise ShellsyNtaxError(
                f"Unrecognised expression type {type!r}",
                ("<string>", 1, 1, string, 1, len(string)),
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
            return eval(
                self.string, self.context, vars(__main__) | vars(shellsy.shell)
            )
        except Exception as e:
            shellsy.shell.console.print_exception(show_locals=True)
            raise ShellsyNtaxError(e)


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

    def __init__(self, name: str, context: Context = context):
        self.name = name
        self.context = context

    def __call__(self, val: Literal = None) -> Literal:
        if val is not None:
            self.context[self.name] = val
        return self.context.get(self.name)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f"${self.name}:{self()!r}"


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
    point_set = digits | set(",")

    if string == "True":
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
            raise ShellsyNtaxError(
                f"unterminated string literal:{string!r}",
                (
                    "<string>",
                    1,
                    pos,
                    full_string or string,
                    1,
                    pos + len(string),
                ),
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
        raise ShellsyNtaxError(
            f"unknown characters {err}" f"in string {string!r}",
            ("<string>", 1, cpos + pos, full_string or string, 1, cpos + pos),
        )
    elif len(string_set - point_set) == 0:
        return Point(
            map(lambda x: float(x) if "." in x else int(x), string.split(","))
        )
    elif len(string) >= 2 and string[0] == "(" and string[-1] == ")":
        if "#" in string and string[: (idx := string.index("#"))].isalpha():
            return Expression(string[:idx], string[idx + 1 : -1])
        return Expression("py", string[1:-1])
    elif len(string) >= 2 and string[0] == "{" and string[-1] == "}":
        return CommandBlock.from_string(string[1:-1])
    raise ShellsyNtaxError(
        f"unrecognised literal:{string!r}",
        ("<string>", 1, pos, full_string or string, 1, pos + len(string)),
    )


class Arguments:
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return f"({self.args}, {self.kwargs})"

    @classmethod
    @annotate
    def from_string(cls, string: str):
        pos = 0
        string_parts = []
        # split string
        while pos < len(string):
            if string[pos] in ("'\""):
                quote = string[pos]
                text = quote
                pos += 1
                while pos < len(string):
                    if string[pos] == "\\":
                        if len(string) == pos + 1:
                            raise ShellsyNtaxError(
                                f"Escaped nothing at end of string:{string!r}",
                                ("<string>", 1, pos, string, 1, pos + 1),
                            )
                        elif string[pos + 1] in ("'\"\\"):
                            text += string[pos + 1]
                            pos += 2
                        else:
                            raise ShellsyNtaxError(
                                f"unknown escape {string[pos:pos+2]!r} in"
                                f" {string!r}",
                                ("<string>", 1, pos, string, 1, pos),
                            )
                    elif string[pos] == quote:
                        pos += 1
                        break
                    else:
                        text += string[pos]
                        pos += 1
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
        args = [
            evaluate_literal(val, pos=pos, full_string=string)
            for pos, val in args
        ]
        kwargs = {
            key: evaluate_literal(val, pos=pos, full_string=string)
            for key, (pos, val) in kwargs.items()
        }
        return Arguments(args, kwargs)
