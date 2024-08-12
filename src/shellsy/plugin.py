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

from pyoload import annotate
from dataclasses import dataclass, field
from typing import Iterable
from setuptools import find_packages
from . import settings
import os
from pathlib import Path


@dataclass
@annotate
class PluginConf:
    name: str
    author: str
    description: str = "A test plugin"
    requirements: tuple[str] = field(default_factory=tuple)


@annotate
def initialize_plugin(
    path: Path | str,
    name: str,
    author: str,
    version: str,
    author_email: str,
    description: str = "A test plugin",
    requirements: Iterable[str] = (),
):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    os.chdir(path)
    open("setup.py", "w").write(
        f"""\
import {name}
from pathlib import Path
from setuptools import setup

project_dir = Path(__file__).parent

try:
    long_description = (project_dir / "README.md").read_text()
except FileNotFoundError:
    long_description = Path("README.md").read_text()

setup(
    name={name!r},
    version={name}.__version__,
    packages=[{name!r}],
    license="MIT",
    author={author!r},
    description={description!r},
    install_requires={requirements!r},
    classifiers=[
        # See https://pypi.org/classifiers/
        "Intended Audience :: Developers",
        'Development Status :: 1 - Planning',
        # "Development Status :: 2 - Pre-Alpha",
        # "Development Status :: 3 - Alpha",
        # 'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
"""
    )
    try:
        os.mkdir(name)
    except FileExistsError:
        pass
    open(f"{name}/__init__.py", "w").write(
        f"""\
{description!r}
__version__ = {version!r}
__author__ = {author!r}

# Do not import anything here!

shellsy_config = {dict()!r}
    """
    )
    open("README.md", "w").write(
        f"""\
# {name}

{description}
"""
    )
    open(f"{name}/shellsy.py", "w").write(
        f"""\
from shellsy.shell import *

class shellsy(Shell):
    @Command
    def __entrypoint__(shell):
        print("hello world!")

    @Command
    def echo(shell, val):
        return val
    """
    )


class Plugin:
    def __init__(self, name):
        self.name = name

    @property
    def shell(self):
        return self.module.shell

    @property
    def module(self):
        return __import__(self.name)

    @classmethod
    def list(cls):
        return list(map(cls, find_packages(settings.plugin_dir)))
