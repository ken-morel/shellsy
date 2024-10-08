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

import json
import os

from .shell import *
from .exceptions import S_Exception
import rich
from pathlib import Path


class Shellsy(Shell):
    """
    Welcome, to shellsy, here you will build simple tools
    """

    intro = """shellsy  Copyright (C) 2024 ken-morel
    This program comes with ABSOLUTELY NO WARRANTY; for details type `w_`.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `c_` for details."""
    _interpreter = None

    def __init__(self):
        self.shellsy = self
        for attr in dir(self):
            if attr == "__entrypoint__":
                self.commands["__entrypoint__"] = getattr(self, attr)
            if attr.startswith("__"):
                continue
            try:
                if isinstance(cmd := getattr(self, attr), Command):
                    cmd.shell = self
                    if attr[0] == "_":
                        attr = attr[1:]
                    self.commands[attr] = cmd
                elif issubclass(subcls := getattr(self, attr), Shell):
                    if attr[0] == "_":
                        attr = attr[1:]
                    self.subshells[attr] = subcls(self)
            except (AttributeError, TypeError):
                pass

    def get_interpreter(self):
        """
        Gets the current shellsy instance interpreter
        :returns: The interpreter instance
        """
        return self._interpreter

    @Command
    def cd(shell, path: Path = None):
        """
        The command to change working directory
        :param path: The path to the new working directory

        :returns: The new working directory
        """
        if path:
            try:
                os.chdir(path)
            except Exception as e:
                print(e)
        return Path(os.getcwd())

    chdir = cd

    class bookmark(Shell):
        @Command
        def __entrypoint__(shell, _: S_Word["as"], name: str):
            """\
            Bookmarks the current directory, or simply adds it to the bookmarks
            list
            :param name: The name to bookmark under
            """
            bookmarks = get_setting("bookmarks", {})
            bookmarks[name] = str(Path(".").resolve())
            set_setting("bookmarks", bookmarks)

        @__entrypoint__.dispatch
        def __entrypoint__2(shell, name: str):
            """\
            Bookmarks the current directory, or simply adds it to the bookmarks
            list
            :param name: The name of bookmark
            """
            bookmarks = get_setting("bookmarks", {})
            if name in bookmarks:
                os.chdir(bookmarks[name])
                StatusText("Moved to !", source="shellsy:.bookmark")
            else:
                print("No such bookmark!")
                return None

    @Command
    def mkdir(shell, path: Path = None):
        """
        The command utility to change directory
        :param path: The new path to assign

        :returns: The new working directory
        """
        try:
            os.makedirs(path)
        except Exception as e:
            print(e)
            return Nil
        else:
            return path

    @Command
    def dir(shell, pattern: str | Path = "*"):
        """
        The command utility to change directory
        :param path: The new path to assign

        :returns: The new working directory
        """
        from rich.markdown import Markdown
        from rich import print

        txt = ""
        for x in Path(".").resolve().glob(str(pattern)):
            txt += f"- {txt}\n"
        print(Markdown(txt))
        return tuple(Path(".").resolve().glob(str(pattern)))

    @Command
    def echo(shell, val):
        """
        Reproduces a value val

        :param val: the value to reproduce

        :returns: val
        """
        return val

    @Command
    def print(shell, val):
        """
        prints the passed value to stdout and returns None
        :param val: the value to print

        :returns: None
        """
        return print(repr(val))

    @Command
    def var(shell, var: S_Variable, val=None):
        """
        setts or gets a variable
        :param var: te variable
        :param val: optional value to sey

        :returns: The variable
        """
        if val is not None:
            var(val)
        return var

    @Command
    def eval(shell, var: Any):
        """
        Returns an evaluated literal
        :param var: The value to eval

        :returns: The evaluate
        """
        return var

    class config(Shell):
        def __entrypoint__(shell, name: str, val: Any = None):
            """\
            config edit configuration settings.

            :param name: The name of the setting to get or set
            :param val: The optional value to assign.

            :returns: THe value of setting 'name'
            """
            if val is not None:
                set_setting(name, val)
            return get_setting(name)

    class status(Shell):
        @Command
        def __entrypoint__(shell):
            """\
            status command prints all the currently showing status messages

            :returns: None
            """
            for x in StatusText.showing:
                pprint(x)
            return None

        @Command
        def add(shell, text: str, dur: int = 5000, source: str = "shell"):
            """
            Creates a new status message in status bar

            :param text: The status text
            :param dur: the status text duration.
            :param source: THe source the status will be attributed.
            Another status of the same source will be overridden if exists.

            :returns: THe status text object
            """
            return StatusText(text, dur, source=source)

        @Command
        def clear(shell):
            """
            Clears all the shown status messages

            :returns: None
            """
            return StatusText.clear()

    class plugin(Shell):
        @Command
        def list(shell):
            """\
            List all available plugins in plugin directory.

            :returns: THe list of plugin names
            """
            from shellsy.plugin import Plugin

            txt = "# Standard modules(installed at `shellsy_path`)\n"
            all = Plugin.list()
            for plug in all:
                txt += f"- `{plug.name}`\n"
            if len(all) == 0:
                txt = "## No module here yet"
            rich.print(Markdown(txt))
            return all

        @Command
        def init(
            shell,
            name: str,
            author: str,
            version: str = "1.0.0",
            path: Path = Path("."),
            author_email: str = "",
            description: str = "A sample shellsy plugin",
            requirements: list = [],
        ):
            """
            initializes a plugin. It creatres a shellsy plugin compatible
            with pip install mechnism, the plugin can then be:

            - Installed to site-packages via `pip install .`
            - Installed to shellsy plugin dir via `shellsy install`
            - Uploaded to pip, view info at [pypi](https://pypi.org/)

            :param name: the plugin name to create. Should match the
            requirements for a python package name. It should preferably be
            different from any other name available at https://pypi.org
            :param author: the plugin author
            :param version: the plugin version, using python versionin syntax
            with X.x.x, as in `1.0.0` or `3.9.7`
            :param path: the plugin path, should be the actuall directory
            :param description: the plugin description, should be not too long
            as more extensive explanation will be avilable in README.md
            :param requirements: the plugin requirements, a list of
            module specs, as [pyoload=2.0.2 comberload==1.1.0]

            :returns: nothing yet, just initializes the plugin
            """
            from shellsy.plugin import initialize_plugin

            return initialize_plugin(
                name=name,
                author=author,
                version=version,
                path=path,
                author_email=author_email,
                description=description,
                requirements=requirements,
            )

        @Command
        def install(shell, path: Path | str = "."):
            """
            Installs the plugin in the current working directory or from
            specified path or pypi package name

            :param path: The optional package name or location
            """
            import os
            from shellsy.settings import plugin_dir

            os.system(f'pip install {path} --target "{plugin_dir}" --upgrade')

    @Command
    def _import(shell, name: str | S_Word):
        """
        Loads the specified module by importing it
        :param name: The name of module to import

        :returns: THe plugin shell or `None` if fails import
        """
        try:
            shell.import_subshell(name)
        except (ImportError, ModuleNotFoundError) as e:
            raise S_Exception(
                str(e).replace("'", "`") + "; _Are you sure it has a_ `.shell`?",
                "import " +  name,
                7,
                name,
            )

    @_import.dispatch
    def _import_as(shell, location: str, _: S_Word["as"], name: str):
        try:
            shell.import_subshell(location, as_=name)
        except (ImportError, ModuleNotFoundError) as e:
            raise S_Exception(
                str(e),
                f"import {lacation} as {name}",
                7,
                lacation,
            )

    @_import.dispatch
    def _import_or_install(
        shell,
        name: str,
        _: S_Word["or"],
        __: S_Word["install"],
        ___: S_Word["from"],
        location: str | Path,
    ):
        try:
            shell.import_subshell(name)
        except (ImportError, ModuleNotFoundError, ShellNotFound):
            try:
                e.show()
            except Exception:
                pass
            import os
            from shellsy.settings import plugin_dir

            os.system(
                "pip install "
                + str(location)
                + ' --target "'
                + str(plugin_dir)
                + '" '
                + "--upgrade"
            )
        finally:
            shell.import_subshell(name)

    class help(Shell):
        @Command
        def __entrypoint__(shell, command: str):
            try:
                command = shell.shellsy.get_command(command)
            except NoSuchCommand:
                raise S_Exception(
                    "No such command",
                    "help " + command,
                    5,
                    command,
                )
            else:
                rich.print(command.help.markdown())

    class json(Shell):
        @Command
        def load(shell, file: Path, var: S_Variable = None):
            """\
            Deserialize a JSON formatted stream to a Python object.

            :param fp: A file-like object containing a JSON document.

            :returns: The resulting object.

            :raises json.JSONDecodeError: If the JSON is malformed or cannot
            be decoded.
                """
            if not file.exists():
                log.error("file does not exist")
            text = file.read_text()
            try:
                data = json.loads(text)
            except Exception as e:
                log.error(e)
            else:
                if var is not None:
                    var.set(data)
                return data

        @load.dispatch
        def _load(shell, text: str, var: S_Variable = None):
            try:
                data = json.loads(text)
            except Exception as e:
                log.error(e)
            else:
                if var is not None:
                    var.set(data)
                return data

        @Command
        def dump(shell, data: Any, file: Path = None, indent: int = None):
            """
            Serialize a Python object to a JSON formatted string.

            :param obj: The Python object to convert to a JSON string.
            :param indent: specifies the number of spaces for indentation.

            :returns: A JSON formatted string representation of the object.
            """
            try:
                text = json.dumps(data, indent=indent)
            except Exception as e:
                log.error(e)
            else:
                if file is not None:
                    try:
                        file.write_text(text)
                    except Exception as e:
                        log.error("error writing to file: " + str(e))
                return text

    class yaml(Shell):
        @Command
        def load(shell, file: Path, var: S_Variable = None):
            import yaml
            if not file.exists():
                return log.error("file does not exist")
            text = file.read_text()
            try:
                data = yaml.safe_loads(text)
            except Exception as e:
                log.error(e)
            else:
                if var is not None:
                    var.set(data)
                return data

        @Command
        def dump(shell, data: Any, file: Path = None):
            try:
                import yaml
            except ImportError:
                return log.error("yaml not installed")
            try:
                text = yaml.safe_dump(data)
            except Exception as e:
                log.error(e)
            else:
                if file is not None:
                    try:
                        file.write_text(text)
                    except Exception as e:
                        log.error("error writing to file: " + str(e))
                return text
