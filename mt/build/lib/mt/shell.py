from shellsy.shell import *


class shell(Shell):
    @Command
    def __entrypoint__(shell):
        print("hello world!")

    @Command
    def mt(shell):
        print("full emptied")
