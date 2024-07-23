from .shell import Command
from .shell import Shell
from .args import Param


class Shellsy(Shell):
    @Command(Param("run"))
    def run(self, args):
        print("running", args)
