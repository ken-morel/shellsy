"""
Shellsy: An extensible shell program designed for ease of use and flexibility.

This module serves as the entry point for the Shellsy application, allowing
users
to define commands and interact with the shell environment.

Copyright (C) 2024 ken-morel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import cmd
import comberload
import os
import rich
import rich.markdown
import time

from rich.console import Console

from ..exceptions import ShellsyException
from ..interpreter import S_Context
from ..interpreter import S_Interpreter
from ..lang import S_Object
from ..settings import data_dir
from ..settings import get_setting
from ..settings import init
from ..shell import Shell
from ..shellsy import Shellsy
from asyncio import ensure_future
from asyncio import Future
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.layout.containers import ConditionalContainer
from prompt_toolkit.layout.containers import Float
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.containers import VSplit
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.containers import WindowAlign
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.widgets import Button
from prompt_toolkit.widgets import Checkbox
from prompt_toolkit.widgets import Dialog
from prompt_toolkit.widgets import Label
from prompt_toolkit.widgets import MenuContainer
from prompt_toolkit.widgets import MenuItem
from prompt_toolkit.widgets import SearchToolbar
from prompt_toolkit.widgets import TextArea
from typing import Optional


init()

INTRO = """
shellsy  Copyright (C) 2022  ken-morel
This program comes with ABSOLUTELY NO WARRANTY; for details type `#@w'.
This is free software, and you are welcome to redistribute it
under certain conditions; type `#@c' for details.
"""
COPYRIGHT_NOTICE = """# License Information

This program is licensed under the **GNU General Public License (GPL)**.

## Key Points of the License:

- **Freedom to Use**: You are free to use this software for any purpose.
- **Access to Source Code**: You can view, modify, and distribute the source
  code.
- **Distribution**: When redistributing the software, you must provide the
  same license terms to others. This ensures that everyone can benefit from the
  freedoms granted by this license.

## Disclaimer:
- This software is provided "as is", without any warranty of any kind, express
  or implied.
- For more details, please read the full text of the
  [GNU General Public License]
  (https://www.gnu.org/licenses/gpl-3.0.html).

## Additional Information:
- If you modify this program and distribute it, you must include a copy of
  this license.
- Please contribute your improvements back to the community when possible.

Thank you for choosing our software and supporting open-source development!
"""
WARANTY_NOTICE = """# Warranty Disclaimer

This program is distributed in the hope that it will be useful,
but **WITHOUT ANY WARRANTY**; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

For more details, refer to the [GNU General Public License]
(https://www.gnu.org/licenses/gpl-3.0.html).

## Important Notes:
- You are advised to test the program extensively before using it in any
critical applications.
- The authors and contributors of this software are not responsible for any
damages that may occur through its use.
- If you encounter any issues, please consider reporting them to the respective
maintainers for potential improvements.

Thank you for using our software!"""


class StatusText:
    __slots__ = ("text", "duration", "source", "begin")
    to_show = []
    shown = []
    showing = []
    cache_size = 50
    source: str
    text: str
    duration: int
    _lexer = None

    def __init__(self, text: str, duration: int, source: str):
        self.text = text
        self.duration = duration
        self.source = source
        StatusText.to_show.append(self)

    @classmethod
    def clear(cls):
        cls.shown.extend(cls.showing)
        cls.showing.clear()

    @classmethod
    def update(cls):
        for idx, stat in reversed(tuple(enumerate(cls.showing[:]))):
            if (time.perf_counter() - stat.begin) > stat.duration:
                cls.showing.pop(idx)
                cls.shown.append(stat)
                cls.shown = cls.shown[-cls.cache_size :]
            for ostat in cls.to_show:
                if ostat.source == stat.source:
                    cls.showing.pop(idx)
                    cls.shown.append(stat)
                    cls.shown = cls.shown[-cls.cache_size :]
        for stat in cls.to_show:
            stat.begin = time.perf_counter()
            cls.showing.append(stat)
        cls.to_show.clear()


class S_Repl(cmd.Cmd):
    """
    ShelsyRepl subclasses cmd.Cmd, and programatically provides the same
    interface.
    check at https://docs.python.org/3.12/library/cmd.html#module-cmd
    """

    interpreter: S_Interpreter
    shouldrun: bool
    context: S_Context
    intro = INTRO
    history = os.path.join(data_dir, "history.txt")
    _lexer = None
    _bindings = None
    _log = ""

    def __init__(
        self,
        interpreter: Optional[S_Interpreter] = None,
        context: Optional[S_Context] = None,
        shell: Optional[Shell] = None,
    ):
        self.console = Console()

        self.context = context or S_Context()
        self.context["out"] = []
        self.context["_"] = None

        self.shell = shell or Shellsy()

        self.interpreter = interpreter or S_Interpreter(
            context=self.context, shell=self.shell
        )

        super().__init__()

    def __call__(self, cmd=None):
        if cmd is None:
            return self.cmdloop()
        else:
            return self.onecmd(cmd)

    def cmdloop(self):
        self.shouldrun = True
        while self.shouldrun:
            command = self.get_input()
            if command is None:
                break
            elif not command.strip():
                continue
            else:
                self.onecmd(command.strip())

    def onecmd(self, command: str):
        if command == "#c_":
            rich.print(rich.markdown.Markdown(COPYRIGHT_NOTICE))
        elif command == "#w_":
            rich.print(rich.markdown.Markdown(WARANTY_NOTICE))
        else:
            try:
                val = self.interpreter.eval(command)
            except ShellsyException as e:
                e.show()
            # except Exception as e:
            #     self.console.print_exception(show_locals=True)
            else:
                self.context["_"] = val
                try:
                    self.context["out"].append(val)
                except Exception:
                    self.context["out"] = [val]
                rich.print(
                    (
                        "[yellow]out[/yellow]@[magenta]"
                        f"{len(self.context['out']) - 1}[/magenta]>"
                    ),
                    repr(val),
                )

    @comberload("prompt_toolkit.lexers")
    def lexer(self):
        from prompt_toolkit.lexers import PygmentsLexer
        from ..lexer import ShellsyLexer

        if self._lexer:
            return self._lexer

        self._lexer = PygmentsLexer(ShellsyLexer)
        return self._lexer

    @comberload(
        "prompt_toolkit.key_binding",
        "prompt_toolkit.application",
    )
    def key_bindings(self):
        if self._bindings is not None:
            return self._bindings

        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.application import run_in_terminal

        bindings = KeyBindings()

        @bindings.add("c-t")
        def _(event):
            "Say 'hello' when `c-t` is pressed."

            def print_hello():
                print("hello world")

            run_in_terminal(print_hello)

        @bindings.add("c-c")
        def _(event):
            "Exit when `c-x` is pressed."

            def print_hello():
                print("exiting gracefully!")

            run_in_terminal(print_hello)
            event.app.exit()

        @bindings.add("c-space")
        def _(event):
            "Initialize autocompletion, or select the next completion."
            buff = event.app.current_buffer
            if buff.complete_state:
                buff.complete_next()
            else:
                buff.start_completion(select_first=False)

        @bindings.add("c-o")
        async def _(event):
            "Open file dialog"
            try:
                from tkinter.filedialog import askopenfilename

                file_path = askopenfilename()
            except Exception as e:
                StatusText(str(e), 5, "__c-o__")
            else:
                buffer = event.app.current_buffer
                # Get the current text and the cursor position
                current_text = buffer.text
                cursor_position = buffer.cursor_position

                # Insert the file path at the current cursor position
                new_text = (
                    current_text[:cursor_position]
                    + "/"
                    + file_path
                    + "/ "
                    + current_text[cursor_position:]
                )
                buffer.text = new_text
                # Move the cursor position to the end of the inserted text
                buffer.cursor_position += len(file_path)

        self._bindings = bindings
        return bindings

    def format_cwd(self):
        import os

        cwd = os.getcwd()
        shortens = ("", "")
        for name, path in os.environ.items():
            if (
                cwd.startswith(path)
                and len(path) > len(name) + 2
                and len(path) > len(shortens[1])
            ):
                shortens = (name, path)
        if shortens[0]:
            return [
                ("class:envpath", "%" + shortens[0] + "%"),
                ("class:cwdpath", cwd[len(shortens[1]) :]),
            ]
        else:
            drive, path = os.path.splitdrive(cwd)
            return [("class:drivename", drive), ("class:cwdpath", path)]

    @comberload("prompt_toolkit.styles", "pygments.styles")
    def get_styles(self):
        from prompt_toolkit.styles import Style
        from prompt_toolkit.styles import style_from_pygments_cls, merge_styles
        from pygments.styles import get_style_by_name

        base_style = style_from_pygments_cls(
            get_style_by_name(get_setting("stylename", "monokai"))
        )
        custom_style = Style.from_dict(
            {
                # "": "#ffffff",
                "shellname": "#884444",
                "envpath": "#88ffaa",
                "drivename": "#0077ff",
                "cwdpath": "#ffff45",
                "prompt": "#00aa00",
                "path": "ansicyan underline",
                "pygments.error": "bg:red",
                "pygments.punctuation": "red",
            }
        )
        return merge_styles([base_style, custom_style])

    @comberload(
        "prompt_toolkit",
        "prompt_toolkit.styles",
        "prompt_toolkit.history",
        "shellsy.lexer",
    )
    def get_input(self):
        import prompt_toolkit
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

        cwd = self.format_cwd()
        return prompt_toolkit.prompt(
            validate_while_typing=True,
            bottom_toolbar=self.bottom_toolbar,
            rprompt=self.right_prompt,
            # enable_history_search=True,
            history=FileHistory(self.history),
            lexer=self.lexer(),
            message=[
                *cwd,
                ("", "\n"),
                ("class:shellname", "%"),
                ("class:prompt", self.prompt),
            ],
            style=self.get_styles(),
            completer=self.shell_completer(),
            auto_suggest=AutoSuggestFromHistory(),
            mouse_support=True,
            key_bindings=self.key_bindings(),
        )

    @get_input.failback
    def raw_get_input(self):
        return input(self.prompt)

    @comberload("prompt_toolkit.completion")
    def shell_completer(self):
        # TDOD: move this to another file and use cls(shell)
        from prompt_toolkit.completion import Completer, Completion

        def similarity(a, b):
            import difflib

            return difflib.SequenceMatcher(lambda *_: False, a, b).ratio()

        class ShellCompleter(Completer):
            def get_completions(_self, document, complete_event):
                # self.get_possible_subcommands()
                from string import ascii_letters
                from pathlib import Path

                line = document.current_line_before_cursor
                # yield Completion(line, start_position=0)
                comps = []
                if len(line) == 0:
                    return
                if (
                    line[0] == "$"
                    and len(set(line[1:]) - set(ascii_letters + "_")) == 0
                ):
                    for v in self.context.resolved():
                        v = "$" + v
                        comps.append((similarity(line[1:], v), v))
                    StatusText(
                        repr(context.get(line[1:])),
                        5,
                        source="__entry-var-values__",
                    )
                    comps.sort(key=lambda k: -k[0])
                    for _, x in comps:
                        yield Completion(x, start_position=-len(line))
                    return
                if (
                    " /" in line
                    and not line.endswith(" /")
                    and len(
                        set(line[line.rindex(" /") + 1 :])
                        - set(ascii_letters + "/\\ :-.")
                    )
                    == 0
                ):
                    *_, fpath = line.rsplit(" /", 1)
                    if "/" in fpath:
                        path, comp = fpath.rsplit("/", 1)
                    else:
                        path, comp = ".", fpath
                    all = Path(path)
                    if all.exists() and all.is_dir():
                        for sub in all.glob("*"):
                            name = str(sub).replace("\\", "/")
                            if sub.is_dir():
                                name += "/"
                            comps.append(
                                (
                                    similarity(str(sub)[-len(comp)], comp),
                                    name,
                                    -len(fpath),
                                )
                            )
                    else:
                        for sword in (
                            "None",
                            "Nil",
                            "True",
                            "False",
                        ):
                            comps.append(
                                (
                                    similarity(line, sword[: len(line)]),
                                    sword,
                                    -len(line),
                                )
                            )
                if " " not in line:
                    for cmd in self.shell.get_possible_subcommands():
                        cmd = cmd.replace(".__entrypoint__", "")
                        comps.append(
                            (
                                similarity(line, cmd[: len(line)]),
                                cmd,
                                -len(line),
                            )
                        )
                elif not line.endswith(" "):
                    _, cline = line.split(" ", 1)
                    if " " in cline and not cline.endswith(" "):
                        _, word = cline.rsplit(" ", 1)
                    else:
                        word = cline
                comps.sort(key=lambda c: -c[0] * 100)
                for _, comp, pos in comps:
                    yield Completion(comp, start_position=pos)

        return ShellCompleter()

    def bottom_toolbar(self):
        from prompt_toolkit import HTML

        try:
            StatusText.update()
        except Exception as e:
            return HTML(
                f"<ansired>{e.__class__.__name__}:</ansired> {e};"
                + ";".join([x.text for x in StatusText.showing])
            )
        else:
            return (
                ";".join([x.text for x in StatusText.showing])
                or "--Nothing Here--"
            )

    def right_prompt(self):
        return ""
