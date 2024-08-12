"""
Shellsy: An extensible shell program designed for ease of use and flexibility.

This module serves as the entry point for the Shellsy application, allowing
users
to define commands and interact with the shell environment.

Copyright (C) 2024  Ken Morel

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

import re

from dataclasses import dataclass
from pygments import unistring as uni
from rich.markdown import Markdown
from typing import Any
from typing import Type
from inspect import _empty


uni_name = f"[{uni.xid_start}][{uni.xid_continue}]*"

param = re.compile(r"\:param (" + uni_name + r")\:")
ret = re.compile(r"\:returns?\:")


@dataclass
class ParamHelp:
    type: Type
    help: str
    name: str
    mode: str
    default: Any

    @classmethod
    def from_param(cls, param, help: str = ""):
        return cls(
            type=param.type,
            name=param.name,
            default=param.default,
            mode=param.mode,
            help=help,
        )


@dataclass
class CommandHelp:
    @staticmethod
    def split_help(help):
        ret_help = begin_help = ""
        param_help = {}
        begin = len(help)
        rest = help
        if m := ret.search(help):
            begin, end = m.span()
            ret_help = help[end:].strip()
            rest = help[:begin]
        if m := param.search(rest):
            b, e = m.span()
            begin_help = rest[:b].strip()
            rest = rest[b:]
        m = param.search(rest)
        while m:
            b, e = m.span()
            name = m.group(1)
            n = param.search(rest[e:])
            if n:
                de, _ = n.span()
                de += e
                param_help[name] = rest[e:de].strip()
                rest = rest[de:]
                m = param.search(rest)
            else:
                param_help[name] = rest[e:].strip()
                m = None
        return begin_help, param_help, ret_help

    @classmethod
    def from_command(cls, cmd):
        begin, params, ret = CommandHelp.split_help(cmd.__func__.__doc__ or "")
        param_help = []
        for param in cmd.params.params:
            if param.name in params:
                param_help.append(ParamHelp.from_param(param, params[param.name]))
        return CommandHelp(
            command=cmd, param_help=param_help, return_help=ret, help=begin
        )

    help: str
    return_help: str
    param_help: list[ParamHelp]
    command: Any

    def markdown(self, **params):
        text = f"# {self.command.name}\n"
        text += f"```python\n{self.command.signature}\n```\n"
        text += self.help + "\n\n"
        for phelp in self.param_help:
            text += f"## ***{phelp.name}***"
            if phelp.type is not _empty:
                text += f" : `{phelp.type}`"
            if phelp.default is not _empty:
                text += f" = `{phelp.default}`, "
            text += "`" + ("/", "/*", "*")[phelp.mode] + "`"
            text += "\n\n"
            for ln in phelp.help.splitlines():
                text += "    " + ln
            text += "\n\n"
        text += "\n## Returns\n\n" + "return_help"
        return Markdown(text)
