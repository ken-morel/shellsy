from .shell import Command
from .shell import Shell


class Shellsy(Shell):
    """
    Welcome, to shellsy, here you will build simple tools
    """
    @Command
    def run(self, cmd: str):
        """
        The command utility
        """
        print("running", cmd)
