"""Generates a width table for Unicode characters.

This script generates a width table for Unicode characters that are not
narrow (width 1). The table is written to src/monochromatic/_width_table.py (note
that although this file is generated, it is checked into Git) and is used
by the char_width() function in src/monochromatic/strings.py.

You should run this script when you upgrade wcwidth, which is expected to
happen when a new Unicode version is released. The generated table contains
the version of wcwidth and Unicode that it was generated for.

In order to run this script, you need to install the latest version of wcwidth.
You can do this by running:

    pip install -U wcwidth

"""

import sys
from collections.abc import Iterable
from os.path import basename, dirname, join

import wcwidth  # type: ignore[import-not-found]


def make_width_table() -> Iterable[tuple[int, int, int]]:
    start_codepoint = -1
    end_codepoint = -1
    range_width = -2
    for codepoint in range(0, sys.maxunicode + 1):
        width = wcwidth.wcwidth(chr(codepoint))
        if width <= 1:
            # Ignore narrow characters along with zero-width characters so that
            # they are treated as single-width.  Note that treating zero-width
            # characters as single-width is consistent with the heuristics built
            # on top of str.isascii() in the str_width() function in strings.py.
            continue
        if start_codepoint < 0:
            start_codepoint = codepoint
            range_width = width
        elif width != range_width or codepoint != end_codepoint + 1:
            yield (start_codepoint, end_codepoint, range_width)
            start_codepoint = codepoint
            range_width = width
        end_codepoint = codepoint
    if start_codepoint >= 0:
        yield (start_codepoint, end_codepoint, range_width)


def main() -> None:
    table_path = join(dirname(__file__), "..", "src", "monochromatic", "_width_table.py")
    with open(table_path, "w") as f:
        f.write(f"""# Generated by {basename(__file__)}
# wcwidth {wcwidth.__version__}
# Unicode {wcwidth.list_versions()[-1]}
from typing import Final

WIDTH_TABLE: Final[list[tuple[int, int, int]]] = [
""")
        for triple in make_width_table():
            f.write(f"    {triple!r},\n")
        f.write("]\n")


if __name__ == "__main__":
    main()
