from pathlib import Path
import os
from .shell import *

import pytest

pytestmark = pytest.mark.skip(reason="Module is not testable, needs run")


class Shellsy(Shell):
    """
    Welcome, to shellsy, here you will build simple tools
    """

    @Command
    def cd(shell, path: Path = None):
        """
        The command utility
        """
        if path:
            try:
                os.chdir(path)
            except Exception as e:
                print(e)
        return Path(os.getcwd())

    chdir = cd

    @Command
    def echo(shell, val):
        return repr(val)

    @Command
    def print(shell, val):
        return print(repr(val))

    @Command
    def var(shell, var: Variable, val=None):
        if val is not None:
            var(val)
        return var

    @Command
    def eval(shell, var: Any):
        return var

    @Command
    def _if(
        shell,
        condition: Expression,
        then: CommandBlock,
        else_: CommandBlock = None,
    ):
        if condition():
            return then.evaluate(shell)
        else:
            if else_ is not None:
                return else_.evaluate(shell)
            return None

    class Config(Shell):
        @Command
        def set(shell, name: str, val):
            settings[name] = val
            return settings.get(name)

        @Command
        def get(shell, name: str):
            return settings.get(name)
