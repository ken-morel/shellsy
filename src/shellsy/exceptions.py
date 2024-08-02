from dataclasses import dataclass
from pyoload import *
from typing import Optional


@dataclass
@annotate
class Stack:
    """Represents a call stack for error reporting in the shell."""
    content: str
    parent_pos: tuple[int, int]
    parent_text: Optional[str]
    file: str

    # @comberload("prompt_toolkit", "pygments")
    def show(self):
        from .shell import Shell
        from prompt_toolkit import print_formatted_text, HTML
        from prompt_toolkit.formatted_text import PygmentsTokens
        import pygments

        file_name = (
            f"<ansicyan>{self.file.replace('>', '&gt;').replace('<', '&lt;')}</ansicyan>"
            if self.file[0] == "<"
            else f"<ansiblue><u>{self.file.replace('>', '&gt;').replace('<', '&lt;')}</u></ansiblue>"
        )
        print_formatted_text(
            HTML(
                f"<ansired>File: </ansired>{file_name}, "
                f"<ansired>line: </ansired><magenta>{self.parent_pos[0]}</magenta>, "
                f"<ansired>Column: </ansired><ansimagenta>{self.parent_pos[1]}</ansimagenta>:"
            )
        )

        try:
            print_formatted_text(
                PygmentsTokens(
                    list(
                        pygments.lex(self.parent_text, lexer=Shell.master.lexer().raw())
                    )
                )
            )
        except AttributeError as e:
            print(self.parent_text)

        print(" " * self.parent_pos[1] + "^" * len(self.content))


@annotate
class StackTrace:
    """Maintains a list of Stack instances for error reporting."""
    stacks: list[Stack]

    def __init__(self):
        self.stacks = []

    def add(self, stack: Stack):
        self.stacks.append(stack)

    def pop(self):
        if self.stacks:
            self.stacks.pop()

    def clear(self):
        self.stacks.clear()

    def show(self):
        """Display the entire stack trace."""
        self.simplify()
        for stack in self.stacks:
            stack.show()

    def simplify(self):
        """Simplify the stack trace by removing repetitive entries."""
        simple = []
        for stack in self.stacks:
            if not simple or simple[-1].parent_text != stack.parent_text:
                simple.append(stack)
        self.stacks[:] = simple


STACKTRACE = StackTrace()


@annotate
class ShellsyError(Exception):
    """Base class for exceptions in the Shellsy application."""
    stacktrace: StackTrace
    message: str

    def __init__(self, msg: str, stacktrace: StackTrace = STACKTRACE):
        self.stacktrace = stacktrace
        self.message = msg

    def show(self):
        self.stacktrace.show()
        print(f"Exception: {self.__class__.__name__} {self.message}")


class ShellsyNtaxError(ShellsyError):
    """Exception raised for syntax errors in Shellsy commands."""
    pass


class ArgumentError(ShellsyError):
    """Exception raised for argument-related errors."""
    pass


class NoSuchCommand(ShellsyError):
    """Exception raised when a command does not exist."""
    def __init__(self, cmd: str, stacktrace: StackTrace = STACKTRACE):
        super().__init__(f"No such command: '{cmd}'", stacktrace)


class ShellNotFound(ShellsyError):
    """Exception raised when the shell cannot be found."""
    pass
