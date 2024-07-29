from shellsy.shell import *


class shellsy(Shell):
    @Command
    def __entrypoint__(shell):
        print("hello world!")

    @Command
    def echo(shell, val):
        return val
