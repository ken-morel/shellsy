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
