from shellsy import Shell, Command


class Cmd(Shell):
    @Command
    def echo(val):
        print(repr(val))


Cmd()()
