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

import sys
from shellsy.shellsy import Shellsy
from shellsy.settings import init


def main(*_):
    """Main entry point for the Shellsy application."""

    try:
        init()
    except Exception as e:
        print(f"Initialization failed: {e}")
        sys.exit(1)

    if len(sys.argv) >= 2:
        file = sys.argv[1]
        if file == "run":
            Shellsy()(sys.argv[2:])
        else:
            run_file(sys.argv[1])
    else:
        enter_command_loop()


def run_file(file_name):
    """Run a shell command file."""
    try:
        Shellsy().run_file(file_name)
    except Exception as e:
        print(f"Error running file {file_name}: {e}")


def enter_command_loop():
    """Start the command loop for interactive shell."""
    Shellsy().cmdloop()


if __name__ == "__main__":
    main()
