"""python -m vocab_builder <command>: the word commands (cli.py) and, after "grammar", the grammar
commands (grammar/cli.py). Without a command: the list of commands."""
import sys


def run():
    if len(sys.argv) > 1 and sys.argv[1] == "grammar":
        from .grammar.cli import main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    else:
        from .cli import main
    main()


if __name__ == "__main__":
    run()
