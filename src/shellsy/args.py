"""
Shellsy: An extensible shell program designed for ease of use and flexibility.

This module serves as the entry point for the Shellsy application, allowing
users
to define commands and interact with the shell environment.

Copyright (C) 2024  Ken Morel

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
from inspect import _empty
from inspect import signature
from .lang import *
from typing import Any


class ShouldDispath(ValueError):
    def __init__(self, exc):
        self.exception = exc


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
        argmaps = []
        if len(string) > 0 and string[0] == "$":
            if "=" in string:
                varname, val = string[1:].split("=", 1)
                val = val.strip()
                argmaps.append((1, varname))
                argmaps.append((len(string) - len(val), val))
                args = Variable(varname.strip()), evaluate_literal(val)
            elif ":" in string:
                from .shell import Shell

                varname, val = string[1:].split(":", 1)
                val = val.strip()
                argmaps.append((1, varname))
                argmaps.append((len(string) - len(val), val))
                args = Variable(varname.strip()), Shell.master(val)
            else:
                argmaps.append((1, string[1:].strip()))
                args = (Variable(string[1:].strip()),)
            STACKTRACE.add(
                Stack(
                    content=string,
                    parent_pos=(1, 0),
                    parent_text=string,
                    file="<call>",
                )
            )
            return cls(
                "var",
                Arguments(
                    args, {}, full_string=string, kwmaps={}, argmaps=argmaps
                ),
            )
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
            STACKTRACE.add(
                Stack(
                    content=args,
                    parent_pos=(1, pos + 1),
                    parent_text=string,
                    file="<call>",
                )
            )
            return cls(cmd, Arguments.from_string(args))

    @classmethod
    @annotate
    def from_string_parts(cls, parts: Iterable[str]):
        if len(parts) == 0:
            name = ""
            args = []
        else:
            name, *args = parts
        return cls(name, Arguments.from_string_parts(args))

    def __str__(self):
        return f"{self.command}{self.arguments}"


