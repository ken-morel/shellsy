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

from .lang import _Parser, S_NameSpace, S_Literal, S_Command
from .exceptions import StackTrace, ShellsyException, S_Exception, WrongLiteral
from .shell import Shell, S_Arguments
from .shellsy import Shellsy
import os

from decimal import Decimal
from pathlib import Path


class S_Interpreter:
    scope: S_NameSpace
    shell: Shell

    def __init__(self):
        self.shell = Shellsy()
        self.stacktrace = StackTrace()

    def eval(self, line: str):
        self.stacktrace.clear()
        command = self.parse_line(line)
        if isinstance(command, S_Command):
            try:
                return command.evaluate()
            except S_Exception as e:
                self.stacktrace.add_stack(e.stack())
                raise ShellsyException(e.msg, self.stacktrace) from e
        else:
            return command

    def parse_line(self, line: str):
        # can be comment or shellsy command
        line = line.rstrip()
        if line.strip().startswith("#"):  # comment, we pass
            return None
        else:  # shellsy command
            cmd, args = self.parse_command(line)
            return S_Command(cmd, args)

    def parse_command(self, call: str):
        pos = 0
        cmd_name, end = _Parser.next_command_name(call, pos)
        self.stacktrace.add(pos, end + 1 if end == pos else end, 0, call, "<command>")
        try:
            command = self.get_command(cmd_name)
        except NoSuchCommand as e:
            raise ShellsyException(e.msg, self.stacktrace)
        self.stacktrace.pop()
        pos = end

        arguments = self.parse_arguments(call, pos)

        return command, arguments

    def get_command(self, name: str):
        return self.shell.get_command(name)

    def parse_arguments(self, string: str, pos: int = 0):
        if string[pos:].strip() == "":
            return S_Arguments([], {}, "")
        else:
            args = []
            kwargs = {}
            last_key = None
            while pos < len(string):
                self.stacktrace.add(pos + 1, len(string), 1, string, "<argument>")
                lit, idx = _Parser.next_key(string, pos)  # try get a key
                if lit is not None:  # found key
                    last_key = (lit, idx - len(lit))
                    kwargs[last_key] = (Nil, None)
                else:
                    try:
                        lit, idx = _Parser.next_literal(string, pos)
                    except _Parser.WrongLiteral as wl:
                        msg, text, begin, pos, end = wl.params
                        self.stacktrace.add(pos, end, 1, text, "<literal>")
                        raise ShellsyException(
                            msg,
                            self.stacktrace,
                        ) from wl
                    else:
                        if lit is None:
                            raise ShellsyException(
                                "Unrecognised literal", self.stacktrace
                            )
                        try:
                            val = self.evaluate_literal(lit, idx - len(lit), string)
                        except WrongLiteral as e:
                            stack = e.stack()
                            if stack.xpos[0] != 0:
                                self.stacktrace.pop()
                                self.stacktrace.add_stack(e.stack())
                            raise ShellsyException(
                                e.msg,
                                self.stacktrace,
                            ) from e

                        v = (val, (idx - len(lit), lit))
                        if last_key is not None:
                            kwargs[last_key] = v
                        else:
                            args.append(v)
                pos = idx
                self.stacktrace.pop()
            return S_Arguments(args, kwargs, string)

    def evaluate_literal(self, string: str, pos=0, full_string=None) -> S_Literal:
        import decimal

        string_set = set(string)
        full_string = full_string or string

        if string == "True":
            return True
        elif string == "False":
            return False
        elif string == "Nil":
            return Nil
        elif string == "None":
            return None
        elif len(string_set - _Parser.INTEGER) == 0:
            return string
        elif len(string_set - _Parser.NUMBER) == 0:
            return string
        elif string[0] == "$":
            return S_Variable(string[1:])
        elif string[0] in _Parser.STRING_QUOTES:
            if string[0] != string[-1]:
                raise WrongLiteral(
                    f"unterminated string literal",
                    full_string,
                    pos + len(string) - 1,
                    string[-1],
                )
            return str(string[1:-1])
        elif string[0] == string[-1] == "/":
            return Path(os.path.expandvars(string[1:-1]))
        elif string[0] == "[" and string[-1] == "]":
            if string == "[]":
                return list()
            elif string == "[-]":
                return dict()
            return string
            # todo: add support for lists
        elif ":" in string and len(string_set - _Parser.NUMBER | _Parser.SLICE) == 0:
            if len(d := (string_set - _Parser.SLICE)) > 0:
                idx = pos + min(string.index(t) for t in d)
                raise WrongLiteral(
                    "wrong slice",
                    full_string,
                    idx,
                    full_string[idx : idx + 1],
                )
            else:
                return slice(*map(int, string.split(":")))
        elif len(string_set - _Parser.POINT) == 0:
            values = []
            pos = 0
            while pos < len(string):
                begin = pos
                if "," in string[pos:]:
                    end = string.index(",", pos)
                else:
                    end = len(string)
                try:
                    dec = Decimal(string[begin:end])
                except decimal.InvalidOperation as e:
                    raise WrongLiteral(
                        str(e),
                        full_string,
                        begin,
                        string[begin:end],
                    ) from e
                else:
                    values.append(dec)
                finally:
                    pos = end + 1
            return S_Point(map(Decimal, string.split(",")))

    def evaluate_expression(self, S_Expression, type, text, context):
        if type not in S_Expression.evaluators:
            raise WrongLiteral(
                f"Unrecognised expression prefix {type!r}",
            )
        return S_Expression.evaluators[type](self, text).evaluate()
