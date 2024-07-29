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
