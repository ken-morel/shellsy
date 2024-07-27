Good day pythonista!

I am here to present to you: shellsy, what is :question:

In your browsing or learning time you surely have used or made several tools,
for:

- Checking sql injection faults
- Or hiding files in images
- Or more

Shellsy brings you a simple way to build and combine all those your tools
in a ready to use, extensible shell application.

Looking also for new feautures, commands or types to integrate in shellsy, so
if you have an idea, please issue it in the bugtracker.

How'a'works?, lets see:

# creating commands

Creating a command is extremely, simple, simply create a function
and decorate it with the `shellsy.Command` class. The command parameters,
default values and types are directly taken from the function definition

lets take a test for this

```python
from shellsy import Shell, Command


class Cmd(Shell):
    @Command
    def echo(shell, val):
        print(repr(val))


Cmd()()
```

we will use that through out examples


# THe command structure

Every shellsy command bases on a command, which is the shell
path to the command seperated by dots, as in `mymodule.config.set`, and then
arguments seperated by spaces and or keyword arguments in the form
`-key optional_value`. The required positional and keyword arguments including
their types and defaults are extracted from the functions signature, making
command creation as straight-forward as defining a function.


# Builtin commands

## if
syntaxes `if (condition) {block1} {optional block2}`
```bash
F:\shellsy\src> shellsy
> if (True) {print 'True is True!'} {print 'True is then not True?'}
'True is True!'
None
F:\shellsy\src> shellsy
> if (not True) {print 'True is True!'} {print 'True is then not True?'}
'True is then not True?'
None
```

# cd and chdir

```bash
F:\shellsy\src> shellsy
> cd
F:\shellsy\src
F:\shellsy\src> shellsy
> cd /C:/Users/CHEF SEC/
C:\Users\CHEF SEC
%USERPROFILE%> shellsy
> cd
C:\Users\CHEF SEC
```
