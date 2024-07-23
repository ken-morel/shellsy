def group(text: str) -> list[str]:
    args = []
    pos = 0
    while pos < len(text):
        while pos < len(text):
            c = text[pos]
            if c in ("'", '"'):
                pos += 1
                begin = pos
                while pos < len(text):
                    if text[pos] == "\\":
                        pos += 2
                    elif text[pos] in ("'", '"'):
                        pos += 2
                        break
                    else:
                        pos += 1
                end = pos - 1
                args.append(text[begin:end])
            elif c.isspace():
                continue
            else:
                begin = pos
                while pos < len(text) and not text[pos].isspace():
                    pos += 1
                end = pos
                pos += 1
                args.append(text[begin:end])
    return args


print(group("hello 'world am I'"))
