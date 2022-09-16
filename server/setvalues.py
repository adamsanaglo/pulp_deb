#!/usr/bin/python3

import sys
from pathlib import Path
from typing import Dict, List


def get_replacements(args: List[str]) -> Dict[str, str]:
    """
    Convert a list of alternating "key" and "value" into a dictionary.
    """
    replacements = {}
    for i in range(0, len(args), 2):
        replacements[args[i]] = args[i + 1]
    return replacements


def main() -> None:
    if len(sys.argv) < 4 or len(sys.argv) % 2 != 0:
        print("Usage: setvalues.py [-s sourcefile] <file> <key> <value> [<key> <value>...]")
        sys.exit(1)
    file = sys.argv[1]
    if file == "-s":
        source = Path(sys.argv[2])
        target = Path(sys.argv[3])
        replacements = get_replacements(sys.argv[4:])
    else:
        source = Path(file)
        target = source
        replacements = get_replacements(sys.argv[2:])

    contents = []
    with source.open("r") as f:
        for line in f.readlines():
            for key, value in replacements.items():
                if key in line:
                    line = line.replace(f'{key}=""', f'{key}="{value}"')
                    break
            contents.append(line)

    with target.open("w") as f:
        f.writelines(contents)


if __name__ == "__main__":
    main()
    sys.exit(0)
