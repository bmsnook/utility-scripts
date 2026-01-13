#!/usr/bin/env python3
"""Parse a pipe-delimited table, store headers and values, and reformat output."""

import sys
import argparse

args = argparse.ArgumentParser(description='Parse a pipe-delimited table, store headers and values, and reformat output.')
# Debug arguments
args.add_argument('-d', '--debug', action='store_true', help='Debug mode')
args.add_argument('file', nargs='?', type=str, help='The file to process (reads from stdin if not provided)')
args.add_argument('--columns', type=int, help='The number of columns to resize')
args.add_argument('--width', type=int, help='The width of the columns')
args.add_argument('--delimiter', type=str, help='The delimiter to use')
args.add_argument('--row_delimiter', type=str, help='The row delimiter to use')
args.add_argument('--column_delimiter', type=str, help='The column delimiter to use')
args.add_argument('--column_spacing', type=str, help='The column spacing to use')

args = args.parse_args()

def parse_table(lines):
    """
    Parse a table with format:
    +-----+---------+------+
    | col1 | col2   | col3 |
    +-----+---------+------+
    | val1 | val2   | val3 |
    +-----+---------+------+

    Returns:
        headers: 2D list of header rows (to support multi-line headers)
        values: 2D list of data rows
        max_lengths: dict mapping column index to max string length
    """
    headers = []      # 2D list: list of header rows, each row is a list of cells
    values = []       # 2D list: list of data rows, each row is a list of cells
    max_lengths = {}

    separator_count = 0
    in_header = True

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # Separator lines start with +
        if line.startswith('+'):
            separator_count += 1
            # After the second separator, we're in the data section
            if separator_count >= 2:
                in_header = False
            continue

        # Parse data row
        parts = line.split('|')
        cells = [cell.strip() for cell in parts[1:-1]]

        # Store in appropriate structure
        if in_header:
            headers.append(cells)
        else:
            values.append(cells)

        # Track max lengths across all cells (headers and values)
        for col_idx, cell in enumerate(cells):
            cell_len = len(cell)
            if col_idx not in max_lengths:
                max_lengths[col_idx] = cell_len
            else:
                max_lengths[col_idx] = max(max_lengths[col_idx], cell_len)

    return headers, values, max_lengths


def format_table(headers, values, max_lengths):
    """
    Format headers and values into a table with:
    - One space between separator and content
    - Headers centered in each column
    - Values left-aligned in each column
    """
    num_cols = len(max_lengths)
    output_lines = []

    # Build separator line
    sep_parts = ['+']
    for col_idx in range(num_cols):
        # Column width + 2 for the single space padding on each side
        sep_parts.append('-' * (max_lengths[col_idx] + 2))
        sep_parts.append('+')
    separator = ''.join(sep_parts)

    # Add top separator
    output_lines.append(separator)

    # Format header rows (centered)
    for header_row in headers:
        row_parts = ['|']
        for col_idx in range(num_cols):
            cell = header_row[col_idx] if col_idx < len(header_row) else ''
            # Center the header with single space padding
            centered = cell.center(max_lengths[col_idx])
            row_parts.append(f' {centered} ')
            row_parts.append('|')
        output_lines.append(''.join(row_parts))

    # Add separator after headers
    if headers:
        output_lines.append(separator)

    # Format value rows (left-aligned)
    for value_row in values:
        row_parts = ['|']
        for col_idx in range(num_cols):
            cell = value_row[col_idx] if col_idx < len(value_row) else ''
            # Left-align the value with single space padding
            padded = cell.ljust(max_lengths[col_idx])
            row_parts.append(f' {padded} ')
            row_parts.append('|')
        output_lines.append(''.join(row_parts))

    # Add bottom separator
    if values:
        output_lines.append(separator)

    return '\n'.join(output_lines)


def main():
    # Read from file if provided, otherwise stdin
    if args.file:
        with open(args.file, 'r') as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()

    headers, values, max_lengths = parse_table(lines)

    if args.debug:
        print("=== Parsed Data ===")
        print(f"Headers (2D list): {headers}")
        print(f"Values (2D list): {values}")
        print(f"Max lengths: {max_lengths}")
        print()
        print("=== Reformatted Table ===")
    print(format_table(headers, values, max_lengths))


if __name__ == '__main__':
    main()
