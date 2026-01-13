#!/usr/bin/env python3
"""Parse a pipe-delimited table, store headers and values, and reformat output."""

import sys
import argparse

args = argparse.ArgumentParser(description='Parse a pipe-delimited table, store headers and values, and reformat output.')
# Debug arguments
args.add_argument('-d', '--debug', action='store_true', help='Debug mode')
args.add_argument('file', nargs='?', type=str, help='The file to process (reads from stdin if not provided)')
args.add_argument('-c', '--columns', type=int, help='Number of columns (from left) to format and output')
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
        max_data_lengths: dict mapping column index to max string length in DATA only
    """
    headers = []      # 2D list: list of header rows, each row is a list of cells
    values = []       # 2D list: list of data rows, each row is a list of cells
    max_data_lengths = {}

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
            # Track max lengths only for DATA cells (not headers)
            for col_idx, cell in enumerate(cells):
                cell_len = len(cell)
                if col_idx not in max_data_lengths:
                    max_data_lengths[col_idx] = cell_len
                else:
                    max_data_lengths[col_idx] = max(max_data_lengths[col_idx], cell_len)

    return headers, values, max_data_lengths


def wrap_header_words(header_text, max_width):
    """
    Wrap a header into multiple lines if it has multiple words and exceeds max_width.
    
    Returns a list of lines for this header cell.
    """
    # If header fits or is a single word, no wrapping needed
    if len(header_text) <= max_width or ' ' not in header_text:
        return [header_text]
    
    words = header_text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= max_width:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines


def compute_wrapped_headers(headers, max_data_lengths):
    """
    Compute wrapped headers and final column widths.
    
    For each column, if the header is longer than data and has multiple words,
    wrap the header words to reduce column width.
    
    Returns:
        wrapped_headers: 2D list of header rows after wrapping
        final_widths: dict mapping column index to final column width
    """
    if not headers:
        return [], max_data_lengths.copy()
    
    num_cols = max(len(row) for row in headers)
    
    # Initialize max_data_lengths for columns that might only have headers
    for col_idx in range(num_cols):
        if col_idx not in max_data_lengths:
            max_data_lengths[col_idx] = 0
    
    # For each column, determine the wrapped header lines
    # wrapped_by_col[col_idx] = list of lines for that column's header
    wrapped_by_col = {}
    final_widths = {}
    
    for col_idx in range(num_cols):
        # Combine all header rows for this column (for single-row headers, just take that)
        # For now, handle the common case of single header row
        header_text = headers[0][col_idx] if col_idx < len(headers[0]) else ''
        
        data_width = max_data_lengths.get(col_idx, 0)
        header_width = len(header_text)
        
        # If header is longer than data and has multiple words, try to wrap
        if header_width > data_width and ' ' in header_text:
            # Find minimum width needed: max of (data_width, longest single word)
            words = header_text.split()
            longest_word = max(len(w) for w in words)
            target_width = max(data_width, longest_word)
            
            wrapped_lines = wrap_header_words(header_text, target_width)
            wrapped_by_col[col_idx] = wrapped_lines
            
            # Final width is max of data width and widest wrapped line
            final_widths[col_idx] = max(data_width, max(len(line) for line in wrapped_lines))
        else:
            # No wrapping needed
            wrapped_by_col[col_idx] = [header_text]
            final_widths[col_idx] = max(data_width, header_width)
    
    # Build the wrapped_headers 2D list
    # Number of header rows = max lines across all columns
    max_header_rows = max(len(lines) for lines in wrapped_by_col.values()) if wrapped_by_col else 1
    
    wrapped_headers = []
    for row_idx in range(max_header_rows):
        row = []
        for col_idx in range(num_cols):
            col_lines = wrapped_by_col.get(col_idx, [''])
            if row_idx < len(col_lines):
                row.append(col_lines[row_idx])
            else:
                row.append('')
        wrapped_headers.append(row)
    
    return wrapped_headers, final_widths


def format_table(headers, values, max_lengths, num_cols=None):
    """
    Format headers and values into a table with:
    - One space between separator and content
    - Headers centered in each column
    - Values left-aligned in each column

    Args:
        num_cols: Number of columns to output (from left). If None, outputs all columns.
    """
    total_cols = len(max_lengths)
    if num_cols is None or num_cols > total_cols:
        num_cols = total_cols
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

    headers, values, max_data_lengths = parse_table(lines)
    wrapped_headers, final_widths = compute_wrapped_headers(headers, max_data_lengths)

    if args.debug:
        print("=== Parsed Data ===")
        print(f"Original Headers: {headers}")
        print(f"Wrapped Headers: {wrapped_headers}")
        print(f"Values (2D list): {values}")
        print(f"Max data lengths: {max_data_lengths}")
        print(f"Final widths: {final_widths}")
        print()
        print("=== Reformatted Table ===")
    print(format_table(wrapped_headers, values, final_widths, args.columns))


if __name__ == '__main__':
    main()
