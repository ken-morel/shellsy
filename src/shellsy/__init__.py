from pathlib import Path
import os
from .shell import Command
from .shell import Shell


class Shellsy(Shell):
    """
    Welcome, to shellsy, here you will build simple tools
    """
    @Command
    def cd(path: Path = None):
        """
        The command utility
        """
        if path:
            os.chdir(path)
        else:
            print(os.getcwd())


__version__ = "1.0.0"
