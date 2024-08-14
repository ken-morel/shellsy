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

from dataclasses import dataclass
from pyoload import annotate
import comberload
from .lang import S_Object

comberload(__package__ + ".lexer", "rich", "rich.panel", "rich.syntax")


class NoSuchCommand(ValueError):
    msg: str

    def __init__(self, msg):
        self.msg = msg


@annotate
class StackTrace:
    """Maintains a list of Stack instances for error reporting."""

    @dataclass
    @annotate
    class Stack:
        """Represents a call stack for error reporting in the shell."""

        xpos: tuple[int, int]
        line: str
        file: str
        ypos: int = 1

        def show(self):
            import rich
            import rich.syntax
            import rich.panel
            from .lexer import lexer

            b, e = self.xpos
            file_name = (
                f"[cyan]{self.file}[/cyan]"
                if self.file[0] == "<"
                else f"[blue underline]{self.file}[/blue underline]"
            )
            file_info = (
                f"File: {file_name}, line: [magenta]{self.ypos}"
                f"[/magenta], Column: [magenta]{b}[/magenta]:"
            )
            rich.print(rich.panel.Panel(file_info, title="[red]At:"))
            rich.print(
                rich.syntax.Syntax(
                    self.line,
                    lexer=lexer,
                    theme="monokai",
                )
            )
            rich.print(" " * b + "^" * (e - b))

        def __eq__(self, other):
            return (
                self.xpos == other.xpos
                and self.line == other.line
                and self.file == other.file
                and self.ypos == other.ypos
            )

    stacks: list[Stack]

    def __init__(self):
        self.stacks = []

    def add(self, begin: int, end: int, row: int, line: str, file: str):
        """add(self, begin: int, end: int, row: int, line: str, file: str):"""
        return self.add_stack(
            StackTrace.Stack(xpos=(begin, end), ypos=row, line=line, file=file)
        )

    def add_stack(self, stack):
        self.stacks.append(stack)

    def pop(self):
        if self.stacks:
            self.stacks.pop()

    def clear(self):
        self.stacks.clear()

    def show(self):
        """Display the entire stack trace."""
        last = None
        for stack in self.stacks:
            if last is None or last != stack:
                stack.show()


@annotate
class ShellsyException(Exception):
    """Base class for exceptions in the Shellsy application."""

    stacktrace: StackTrace
    message: str

    def __init__(self, msg: str, stacktrace):
        self.stacktrace = stacktrace
        self.message = msg

    def show(self):
        self.stacktrace.show()
        print(f"Exception: {self.__class__.__name__} {self.message}")


class S_Exception(S_Object, Exception):
    def __init__(
        self,
        message: str,
        fullstring: str = "",
        pos: int = 0,
        child: str = "",
        file: str = "<expr>",
        row: int = 0,
    ):
        self.string = fullstring
        self.idxs = (pos, pos + len(child))
        self.file = file
        self.msg = message
        super().__init__(message)

    def stack(self):
        return StackTrace.Stack(
            xpos=self.idxs,
            line=self.string,
            file=self.file,
            ypos=1,
        )


class WrongLiteral(S_Exception):
    @annotate
    def __init__(self, message: str, fullstring: str, pos: int, part: str):
        super().__init__(message, fullstring, pos, part, "<literal>", 0)


class ArgumentError(S_Exception):
    @annotate
    def __init__(self, message: str, fullstring: str, pos: int, part: str):
        super().__init__(message, fullstring, pos, part, "<literal>", 0)
