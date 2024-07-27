from dataclasses import dataclass
from pyoload import *
from typing import Optional


@dataclass
@annotate
class Stack:
    content: str
    parent_pos: tuple[int, int]
    parent_text: Optional[str]
    file: str

    def show(self):
        print(
            "File " + self.file + f", line {self.parent_pos[0]},",
            f"column {self.parent_pos[1]}",
        )
        print(self.parent_text or self.content)
        print(" " * self.parent_pos[1] + "^" * len(self.content))


class StackTrace:
    def __init__(self):
        self.stacks = []

    def add(self, stack):
        self.stacks.append(stack)

    def pop(self):
        self.stacks.pop()

    def clear(self):
        self.stacks.clear()

    def show(self):
        for stack in self.stacks:
            stack.show()


STACKTRACE = StackTrace()


class ShellsyError(Exception):
    def __init__(self, msg, stacktrace=STACKTRACE):
        self.stacktrace = stacktrace
        self.message = msg

    def show(self):
        self.stacktrace.show()
        print("Exception: ", self.__class__.__name__, self.message)


class ShellsyNtaxError(ShellsyError):
    pass


class ArgumentError(ShellsyError):
    pass


class NoSuchCommand(ShellsyError):
    pass
