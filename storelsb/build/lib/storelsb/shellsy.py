from shellsy.shell import *

print("hela")


class shellsy(Shell):
    @Command
    def __entrypoint__(shell):
        print("hello world!")

    @Command
    def echo(shell, val):
        return val

print("but i do!" * 100)
