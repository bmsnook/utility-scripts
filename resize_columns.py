#!/usr/bin/env python3
"""Parse a pipe-delimited table and find the max string length per column."""

import sys


def parse_table(lines):
    """
    Parse a table with format:
    +-----+---------+------+
    | col1 | col2   | col3 |
    +-----+---------+------+
    | val1 | val2   | val3 |
    +-----+---------+------+

    Returns a dict mapping column index (0-based) to max string length.
    """
    max_lengths = {}

    for line in lines:
        line = line.strip()

        # Skip separator lines (start with +)
        if not line or line.startswith('+'):
            continue

        # Split by | and strip whitespace from each cell
        # The split gives empty strings at start/end due to leading/trailing |
        parts = line.split('|')

        # Remove empty strings from leading/trailing pipes
        cells = [cell.strip() for cell in parts[1:-1]]

        for col_idx, cell in enumerate(cells):
            cell_len = len(cell)
            if col_idx not in max_lengths:
                max_lengths[col_idx] = cell_len
            else:
                max_lengths[col_idx] = max(max_lengths[col_idx], cell_len)

    return max_lengths


def main():
    # Read from stdin or a file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()

    max_lengths = parse_table(lines)

    print("Column max lengths:")
    for col, length in sorted(max_lengths.items()):
        print(f"  Column {col}: {length}")


if __name__ == '__main__':
    main()

