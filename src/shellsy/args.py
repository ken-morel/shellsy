from inspect import _empty
from inspect import ismethod
from inspect import signature
from pyoload import *
from typing import Callable
from typing import Iterable
from typing import Type
from pathlib import Path
from decimal import Decimal


class Context(dict):
    pass


context = Context()


class ShellsyCustomType:
    pass


class CommandBlock(ShellsyCustomType):
    commands: Iterable[str]

    def __init__(self, commands: Iterable[str]):
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
    context: Context

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
    prefix = ">"

    def evaluate(self):
        return eval(self.string, self.context)


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


class NilType:
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


class ShellsyNtaxError(SyntaxError):
    def show(self):
        print(self)


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
    elif ":" in string:
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
        return Expression(string[1], string[2:-1])
    elif len(string) >= 2 and string[0] == "{" and string[-1] == "}":
        return CommandBlock.from_string(string[1:-1])
    raise ShellsyNtaxError(f"Unrecognised literal: {string!r}")


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
        string_parts = [""]
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
                                f"Escaped nothing at end of string:{string!r}"
                            )
                        elif string[pos + 1] in ("'\"\\"):
                            text += string[pos + 1]
                            pos += 2
                        else:
                            raise ShellsyNtaxError(
                                f"unknown escape {string[pos:pos+2]!r} in"
                                f" {string!r}"
                            )
                    elif string[pos] == quote:
                        pos += 1
                        break
                    else:
                        text += string[pos]
                        pos += 1
                string_parts.append(text + quote)
            elif string[pos] == "/":
                begin = pos
                pos += 1
                while pos < len(string) and not (
                    string[pos] == "/"
                    and (len(string) == pos + 1 or string[pos + 1].isspace())
                ):
                    pos += 1
                string_parts.append(string[begin : pos + 1])
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
                string_parts.append(string[begin : pos + 1])
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
                string_parts.append(string[begin : pos + 1])
            elif not string[pos].isspace():
                begin = pos
                while len(string) > pos and not string[pos].isspace():
                    pos += 1
                string_parts.append(string[begin:pos])
            pos += 1
        del pos
        return cls.from_string_parts(tuple(filter(bool, string_parts)))

    @classmethod
    @annotate
    def from_string_parts(cls, string_parts: Iterable[str]):
        args = []
        kwargs = {}

        def is_key(string):
            return string[0] == "-" and len(string) > 1 and string[1].isalpha()

        idx = 0
        while idx < len(string_parts):
            part = string_parts[idx]
            if is_key(part):
                key = part[1:]
                if idx + 1 < len(string_parts):
                    if is_key(string_parts[idx + 1]):
                        val = "Nil"
                    else:
                        val = string_parts[idx + 1]
                        idx += 1
                kwargs[key] = val
            else:
                args.append(part)
            idx += 1
        # evaluate literals
        args = tuple(map(evaluate_literal, args))
        kwargs = dict(zip(kwargs, map(evaluate_literal, kwargs.values())))
        return Arguments(args, kwargs)


@annotate
class CommandCall:
    command: str
    arguments: Arguments

    def __init__(self, cmd: str, args: Arguments):
        self.command = cmd
        self.arguments = args

    def inner(self):
        cmd, *rest = self.command.split(".")
        return cmd, CommandCall(".".join(rest), self.arguments)

    @classmethod
    @annotate
    def from_string(cls, string: str):
        if len(string) > 0 and string[0] == "$":
            if ":" in string:
                varname, val = string[1:].split(":", 1)
                args = Variable(varname.strip()), evaluate_literal(val.strip())
            else:
                args = (Variable(string[1:].strip()),)
            return cls("var", Arguments(args, {}))
        else:
            cmd = ""
            args = ""
            pos = 0
            while pos < len(string) and (
                string[pos].isalnum() or string[pos] in "._"
            ):
                pos += 1
            cmd = string[:pos]
            args = string[pos:].strip()
            return cls(cmd, Arguments.from_string(args))

    @classmethod
    @annotate
    def from_string_parts(cls, parts: Iterable[str]):
        name, *args = parts
        return cls(name, args)

    def __str__(self):
        return f"<Command:{self.command}{self.arguments}>"


class CommandParameter:
    def __init__(self, name: str, type: None, default: None, mode: int):
        self.name = name
        self.type = type
        self.default = default
        self.mode = mode

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
        return f"<{self.name}: {self.type} = {self.default}, {mode}>"


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
    def bind(self, args: Arguments) -> dict[str, Literal]:
        kwargs = {}
        for idx, param in enumerate(self.params):
            if param.name in args.kwargs:
                kwargs[param] = args.kwargs[param.name]
            elif len(args.args) > idx:
                kwargs[param] = args.args[idx]
            elif param.default is not _empty:
                kwargs[param] = param.default
            else:
                raise ValueError(f"missing argument for {param}")
        final_args = {}
        for param, val in kwargs.items():
            if val == param.default:
                final_args[param.name] = val
                continue
            if isinstance(val, Variable) and param.type not in (
                _empty,
                Variable,
            ):
                val = val()
            if isinstance(val, Expression) and param.type not in (
                _empty,
                Expression,
            ):
                val = val()
            if param.type is not _empty and not isinstance(val, param.type):
                idx = -1
                if val in args.args:
                    idx = args.args.index(val)
                raise ArgumentTypeMismatch(param, val)
            final_args[param.name] = val
        return final_args

    def __str__(self):
        return f"<CommandParameters:[{', '.join(map(str, self.params))}]>"
