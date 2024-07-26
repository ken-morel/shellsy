from pathlib import Path
import os
from .shell import *

import pytest

pytestmark = pytest.mark.skip(reason="Module is not testable, needs run")


class Shellsy(Shell):
    """
    Welcome, to shellsy, here you will build simple tools
    """

    @Command
    def cd(shell, path: Path = None):
        """
        The command utility to change directory
        :param path: The new path to assign

        :returns: The new working directory
        """
        if path:
            try:
                os.chdir(path)
            except Exception as e:
                print(e)
        return Path(os.getcwd())

    chdir = cd

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

    @Command
    def echo(shell, val):
        """
        Reproduces a value val

        :param val: the value to reproduce

        :returns: val
        """
        return repr(val)

    @Command
    def print(shell, val):
        """
        prints the passed value to stdout and returns None
        :param val: the value to print

        :returns: None
        """
        return print(repr(val))

    @Command
    def var(shell, var: Variable, val=None):
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

    @Command
    def _if(
        shell,
        condition: Expression,
        then: CommandBlock,
        __: Word["else"] = None,
        else_: CommandBlock = None,
    ):
        """
        if condition in the form `if (condition) {then} else {else}`

        :param condition: the condition switch
        :param pass: THe code block to run on pass
        """
        if condition():
            return then.evaluate(shell)
        else:
            if else_ is not None:
                return else_.evaluate(shell)
            return None

    @Command
    def _while(
        shell,
        condition: Expression,
        then: CommandBlock,
    ):
        ret = None
        while condition():
            ret = then.evaluate(shell)

        return ret

    class config(Shell):
        @Command
        def set(shell, name: str, val: Any):
            set_setting(name, val)
            return get_setting(name)

        @Command
        def get(shell, name: str):
            return get_setting(name)

    class status(Shell):
        @Command
        def __entrypoint__(shell):
            for x in StatusText.showing:
                pprint(x)
            return None

        @Command
        def add(shell, text: str, dur: int = 5000):
            return StatusText(text, dur)

        @Command
        def clear(shell):
            return StatusText.clear()

    class plugin(Shell):
        @Command
        def list(shell):
            from shellsy.plugin import Plugin

            txt = ""
            all = Plugin.list()
            for plug in all:
                txt += f"- {plug.name} at {plug.module.__file__}\n"
            if len(all) == 0:
                txt = "# No module here yet"
            pprint(Markdown(txt))
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
        def install(shell):
            import os
            from shellsy.settings import plugin_dir

            os.system('pip install . --target "' + str(plugin_dir) + '"')

        @Command
        def load(shell, name: str):
            """
            Loads the specified module by importing it
            :param name: The name of module to import

            :returns: THe plugin shell or `None` if fails import
            """
            try:
                mod = __import__(name + ".shell")
            except (ImportError, ModuleNotFoundError) as e:
                print(e)
            try:
                plugin_shell = mod.shell.shell
            except AttributeError as e:
                print("Module shell not found:", e)
            else:
                from shellsy.lexer import for_shell
                shell.master.subshells[name] = plugin_shell(
                    parent=shell.master
                )
                shell.master._lexer = for_shell(shell.master)
                return shell

    class help(Shell):
        @Command
        def __entrypoint__(shell, command: str = None):
            if command:
                pprint(shell.master.get_command(command).help.markdown())
            else:
                print("no command specified")
