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
