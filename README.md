Good day pythonista!

I am here to present to you: shellsy, what is :question:

In your browsing or learning time you surely have used or made several tools,
for:

- Checking sql injection faults
- Or hiding files in images
- Or more

Shellsy bringsnyou a simple way to build and combing all those your tools
in a ready to use, extensible shell application.

It is still in dev and does not completely integrates the extensible feature,
but I am going there to make shellsy uable, fast and extensible enough to
help you in you  day to day life.

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
    def echo(val):
        print(repr(val))


Cmd()()
```

we will use that througn out examples

## available types

### int

Integer simply an integer value

```bash
F:\shellsy\src> cmd
> echo 3
3
```

### Decimal

any decimal value

```bash
F:\shellsy\src> cmd
> echo 3.5
Decimal('3.5')
```
### string

Simply quote with single or double quote

```bash
F:\shellsy\src> cmd
> echo '37+83 ljd'
'37+83 ljd'
```

### path

path are contained in `//` escapes, they can be relative or absolute

```bash
F:\shellsy\src> cmd
> echo /C:/Users/
WindowsPath('C:/Users')
```

### slice

a slice to be used as a range or more, using the python array index syntax
`begin:end:skip`, the three MUST be specified

```bash
F:\shellsy\src> cmd
> echo 3:4:5
slice(3, 4, 5)
```

### Point

A point value, uses simple `x,y` or `x,y,z` syntax with no space between, is
a subclass of tuple and supports adding more than three dimensions as:
`12,-34,-4,04,4`
returns a
`shellsy.args.Point(tuple)`.

```bash
F:\shellsy\src> cmd
> echo 3,5
Point(3.0, 5.0)
F:\shellsy\src> cmd
> echo 3,5,-45,23,34
Point(3.0, 5.0, -45.0, 23.0, 34.0)
```
