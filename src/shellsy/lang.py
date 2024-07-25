from decimal import Decimal
from pathlib import Path
from pyoload import *
from typing import Iterable


class Context(dict):
    pass


context = Context()


class ShellsyNtaxError(SyntaxError):
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
        return "<shellsy.Nil>"

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
        return f":{self.name}:"

    def __hash__(self):
        return hash(self.name)

    class _Word:
        _instance = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = object.__new__(cls)
            return cls._instance


Word.add("as")
Word.add("else")


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
            raise ShellsyNtaxError(f"Unrecognised expression type {type!r}")

    def __call__(self):
        return Expression.evaluate(self.type, self.string, self.context)

    @classmethod
    def evaluate(cls, type, string, context):
        if type not in cls.evaluators:
            raise ShellsyNtaxError(f"unknown expression prefix, {type}")
        return cls.evaluators[type](context, string).evaluate()

    def __repr__(self):
        return f"<Expression({self.type}:{self.string})>"

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
        import traceback
        import __main__

        try:
            return eval(self.string, self.context, vars(__main__))
        except Exception as e:
            from shellsy.shell import console

            console.print_exception(show_locals=True)
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
def evaluate_literal(string: str) -> Literal:
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
            raise ShellsyNtaxError(f"unterminated string literal:{string!r}")
        return str(string[1:-1])
    elif string[0] == string[-1] == "/":
        return Path(string[1:-1])
    elif ":" in string and len(string_set - slice_set) == 0:
        if len(string_set - slice_set) == 0:
            return slice(*map(int, string.split(":")))
        raise ShellsyNtaxError(
            f"unknown characters {string_set - slice_set}"
            f"in string {string!r}"
        )
    elif len(string_set - point_set) == 0:
        return Point(
            map(lambda x: float(x) if "." in x else int(x), string.split(","))
        )
    elif len(string) >= 3 and string[0] == "(" and string[-1] == ")":
        if "#" in string and string[: (idx := string.index("#"))].isalpha():
            return Expression(string[:idx], string[idx + 1 :])
        return Expression("py", string)
    elif len(string) >= 2 and string[0] == "{" and string[-1] == "}":
        return CommandBlock.from_string(string[1:-1])
    raise ShellsyNtaxError(f"Unrecognised literal: {string!r}")
