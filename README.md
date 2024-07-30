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

# Building shellsy ceasar

first, we will install shellsy:

## Installation

You can still only install shellsy form github with

```bash
git clone https://github.com/ken-morel/shellsy.git
cd shellsy/src
pip install .
```

## Initializig the plugin

Simply navigate to an empty directory and use `plugin.init` command

```bash
PS F:\> shellsy
shellsy  Copyright (C) 2024  ken-morel
This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
This is free software, and you are welcome to redistribute it
under certain conditions; type `show c' for details.
F:\> shellsy
> cd /shellsy/
@0> F:\shellsy
F:\shellsy> shellsy
> mkdir /ceasar/
@1> None
F:\shellsy> shellsy
> cd /ceasar/
@2> F:\shellsy\ceasar
F:\shellsy\ceasar> shellsy
> plugin.init "ceasar" "ken-morel"
@3> None
```

This should give you this directory tree:

```bash
F:\shellsy\ceasar> shellsy
> !tree /f
Folder PATH listing
Volume serial number is 0084E71C 8452:4B29
F:.
│   README.md
│   setup.py
│
└───ceasar
        shellsy.py
        __init__.py

@6> 0
```

The setup is that of a simple python module. The special thing we will build
here is the shellsy.py which contains the entry point to your shell.

## Writting the ceasar function

I will do that in _ceasar/ceasar.py_

```py
from pathlib import Path


def char_ceasar(char: chr, offset: int, letter) -> chr:
    c = ord(char)
    a, z = ord("a"), ord("z")
    A, Z = ord("A"), ord("Z")
    if not letter or (a <= c <= z or A <= c <= Z):
        nc = c + offset
        if (char.isupper() and nc > Z) or (char.islower() and nc > z):
            nc -= 26
        if (char.isupper() and nc < A) or (char.islower() and nc < a):
            nc += 26
        return chr(nc)
    else:
        return char


def ceasar_file(infile: Path, outfile: Path, offset: int, ch_only):
    """\
    Does ceasar on the file using the ceasar() function

    :param infile: The file to perform the ceasar on
    :param outfile: The file to write the output to

    :param offset: THe amount to offset
    :param ch_only: to ceasar only letters, default true
    """
    with open(infile) as f:
        intext = f.read()

    outtext = ceasar_text(intext, offset, ch_only)

    with open(outfile) as f:
        f.write(outtext)


def ceasar_text(text: str, offset, ch_only) -> str:
    return "".join(map(lambda c: char_ceasar(c, offset, ch_only), text))

```

we can test it:

```python
>>> ceasar_text("please GPT, what could have been the name given to the gravitational rate of change of linear momentum in the binomial system of nomenclature?", 7, True)
'wslhzl NWA, doha jvbsk ohcl illu aol uhtl npclu av aol nyhcpahapvuhs yhal vm johunl vm spulhy tvtluabt pu aol ipuvtphs zfzalt vm uvtlujshabyl?'
>>> ceasar_text("please GPT, what could have been the name given to the gravitational rate of change of linear momentum in the binomial system of nomenclature?", 7, False)
"wslhzl'NWA3'doha'jvbsk'ohcl'illu'aol'uhtl'npclu'av'aol'nyhcpahapvuhs'yhal'vm'johunl'vm'spulhy'tvtluabt'pu'aol'ipuvtphs'zfzalt'vm'uvtlujshabylF"   # ceasars too the spaces and punctuation
```


now we will create a shell interface


```python
from shellsy.shell import *
from . import ceasar
from random import choice


class shellsy(Shell):  # creating the subshell!
    @Command
    def ceasar(
        shell,
        text: str,
        offset: int | slice = slice(1, 26),
        nonletters: Nil = None,
    ):  # the ceasar function
        """performs ceasar on text or file
        :param text:  THe text to perfoem ceasar on
        :param offset: the integer offset to apply, or a slice range to select
        value from.
        :param letters:  If ceasar should only touch letters: default True

        :returns: The ceasar cipher
        """  # SOme docs for help
        if isinstance(offset, slice):
            offset = choice(range(offset.start, offset.stop, offset.step or 1))

        return ceasar.ceasar_text(text, offset, nonletters is None)

    @ceasar.dispatch  # A second function for files
    def ceasar2(
        shell,
        infile: Path,
        outfile: Path = None,
        offset: int | slice = slice(1, 26),
        nonletters: Nil = None,
    ):
        if isinstance(offset, slice):
            offset = choice(range(offset.start, offset.stop, offset.step or 1))
        return ceasar.ceasar_file(
            infile, outfile or infile, offset, nonletters is None
        )
```

Word perfect! we now have our complete module, lets now install it.
with `plugin.install`

```bash
F:\shellsy\ceasar> shellsy
> plugin.install
Processing f:\shellsy\ceasar
  Preparing metadata (setup.py) ... done
Building wheels for collected packages: ceasar
  Building wheel for ceasar (setup.py) ... done
  [... SNIPPED ...]
Successfully built ceasar
Installing collected packages: ceasar
Successfully installed ceasar-1.0.0
```

Now we can import it, and test it!

```bash
> import 'ceasar'
@2> None
F:\shellsy\ceasar> shellsy
> help 'ceasar.ceasar'
                                   ceasar

(shell, text: str, offset: int | slice = slice(1, 26, None), nonletters: Nil = None)

performs ceasar on text or file

                            text : <class 'str'>/*

THe text to perfoem ceasar on

                offset : int | slice = slice(1, 26, None), /*

the integer offset to apply, or a slice range to select            value from.
@3> None
F:\shellsy\ceasar> shellsy
> ceasar.ceasar "hello world"
@4> mjqqt btwqi
F:\shellsy\ceasar> shellsy
> ceasar.ceasar "hello world" -nonletters
@5> tqxxa,iadxp
F:\shellsy\ceasar> shellsy
> ceasar.ceasar "hello world" 1 -nonletters
@6> ifmmp!xpsme
F:\shellsy\ceasar> shellsy
> ceasar.ceasar "hello world" 0
@7> hello world
F:\shellsy\ceasar> shellsy
> ceasar.ceasar "hello world" 5:6
@8> mjqqt btwqi
F:\shellsy\ceasar> shellsy
>
```

Gives perfectly!. well, you are set now.
For more docs, you will have in the github wiki at https://gitub.com/ken-morel/shellsy/wiki
