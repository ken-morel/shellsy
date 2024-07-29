from pathlib import Path
import os
from .shell import *

import pytest

pytestmark = pytest.mark.skip(reason="Module is not testable, needs run")


class Shellsy(Shell):
    """
    Welcome, to shellsy, here you will build simple tools
    """

    intro = """shellsy  Copyright (C) 2024  ken-morel
This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
This is free software, and you are welcome to redistribute it
under certain conditions; type `show c' for details."""

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
            Evaluates a condition and executes a command block if the condition
             is met.
            If the condition is not met and an else block is provided,
            the else block is executed.

            :param condition: The condition to evaluate before executing the
            'then' block. It should be a function that returns a boolean value.
            :param then: The command block to execute if the condition is met.
             This block contains the commands to run when the condition is true
            :param else_: Optional - The command block to execute if the
            condition is not met. If provided, this block will be executed when
            the condition is false.

            :returns: The result of executing the 'then' block or the 'else'
            block if the condition is not met.

            For example:
            if (x > 5) {echo 'x > 5'} else {echo 'x <= 5'}

            [[2]](https://poe.com/citation?message_id=224987918374&citation=2)
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
        """
        The 'while' command in shellsy creates a loop that iterates as long as
        a specified condition is met. This command enables the repetitive
        execution of a block of commands until the condition evaluates to False

        :param condition: The condition parameter defines the expression to be
        evaluated in each iteration of the loop. The 'while' command will
        continue executing the associated block of commands as long as this
        condition remains True. It serves as the criteria for determining the
        loop's continuation

        :param command_block: The command_block parameter represents the block
        of commands that will be executed repeatedly as part of the 'while'
        loop. This block contains the actions or logic that should be performed
        iteratively until the condition evaluates to False. It encapsulates the
        commands to be executed within the loop structure

        :returns: The 'while' command does not have an explicit return value,
        as its primary function is to facilitate iterative execution based on
        the specified condition. The execution of the command_block within the
        loop allows for repetitive actions until the condition becomes False.
        The return value is determined by the commands executed within the loop

        Example usage:
        _while(lambda: x > 5, CommandBlock(...))

        Utilize the 'while' command in shellsy with the provided parameters and
        syntax to implement loops that perform repetitive actions based on
        defined conditions.
        This feature enhances the flexibility and functionality of your scripts
        by enabling iterative execution of commands until a specific condition
        is no longer met
        """
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

            os.system(
                'pip install . --target "' + str(plugin_dir) + '" --upgrade'
            )

        @install.dispatch
        def install_from(shell, location: Path | str):
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

    @Command
    def _import(shell, name: str):
        """
        Loads the specified module by importing it
        :param name: The name of module to import

        :returns: THe plugin shell or `None` if fails import
        """
        try:
            shell.import_subshell(name)
        except (ImportError, ModuleNotFoundError) as e:
            print(e)

    @_import.dispatch
    def _import_as(shell, location: str, _: Word["as"], name: str):
        try:
            shell.import_subshell(location, name)
        except (ImportError, ModuleNotFoundError) as e:
            print(e)

    @_import.dispatch
    def _import_or_install(
        shell,
        name: str,
        _: Word["or"],
        __: Word["install"],
        ___: Word["from"],
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
        def __entrypoint__(shell, command: str = None):
            if command:
                pprint(shell.master.get_command(command).help.markdown())
            else:
                print("no command specified")

    @Command
    def exit(shell):
        shell.should_run = False
