"""Page range parsing utilities for QPDF-style page specifications."""

from typing import Optional


def parse_page_range(page_range: Optional[str], total_pages: int) -> list[int]:
    """
    Parse a QPDF-style page range string into a list of 0-indexed page numbers.

    See https://qpdf.readthedocs.io/en/stable/cli.html#page-ranges

    Follows QPDF page range specification:
    - Plain numbers (1-indexed): "1" = first page, "5" = fifth page
    - r-prefix counts from end: "r1" = last page, "r2" = second-to-last
    - z = last page (same as r1)
    - Ranges with dash: "1-5" = pages 1-5, "5-1" = pages 5,4,3,2,1 (reversed)
    - Comma-separated: "1,3,5" = pages 1, 3, and 5
    - :odd/:even filters: "1-10:even" = even positions from range
    - x-prefix excludes: "1-10,x3-4" = pages 1,2,5,6,7,8,9,10

    Examples:
        "1-5" -> [0, 1, 2, 3, 4]
        "r3-r1" -> last three pages
        "z-1" -> all pages reversed
        "1-20:even" -> [1, 3, 5, 7, 9, 11, 13, 15, 17, 19] (even positions)
        "1-10,x3-4" -> [0, 1, 4, 5, 6, 7, 8, 9]
        "5,7-9,12:odd" -> [4, 7, 11] (odd positions from [5,7,8,9,12])

    Args:
        page_range: QPDF-style page range string, or None for all pages
        total_pages: Total number of pages in the PDF

    Returns:
        List of 0-indexed page numbers

    Raises:
        ValueError: If the page range format is invalid or pages are out of range
    """
    if page_range is None or page_range == "":
        return list(range(total_pages))

    # Check if there's a top-level filter (applies to entire expression)
    filter_type = None
    if ':' in page_range:
        # Check if the colon is part of a top-level filter
        # It's top-level if it appears after the last comma or if there are no commas
        last_colon_idx = page_range.rfind(':')
        last_comma_idx = page_range.rfind(',')

        # If colon comes after last comma, it's a top-level filter
        if last_colon_idx > last_comma_idx:
            main_part, filter_str = page_range.rsplit(':', 1)
            filter_str = filter_str.strip().lower()
            if filter_str in ('odd', 'even'):
                filter_type = filter_str
                page_range = main_part
            elif filter_str:  # Non-empty but invalid filter
                raise ValueError(f"Invalid filter: '{filter_str}'. Must be 'odd' or 'even'")

    def resolve_page_num(s: str) -> int:
        """Convert page reference to 1-indexed page number."""
        s = s.strip()
        if s == 'z':
            return total_pages
        elif s.startswith('r'):
            # r1 = last, r2 = second-to-last, etc.
            offset = int(s[1:])
            return total_pages - offset + 1
        else:
            return int(s)

    def parse_simple_part(part: str) -> list[int]:
        """Parse a single range part without filters."""
        part = part.strip()

        # Parse the range or single page
        if '-' in part:
            # Range like "1-5" or "r3-r1"
            start_str, end_str = part.split('-', 1)
            start = resolve_page_num(start_str)
            end = resolve_page_num(end_str)

            # Generate range (forward or backward)
            if start <= end:
                return list(range(start, end + 1))
            else:
                return list(range(start, end - 1, -1))
        else:
            # Single page
            page_num = resolve_page_num(part)
            return [page_num]

    # Split by commas and process each part
    parts = page_range.split(',')
    pages = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith('x'):
            # Exclusion range - remove these pages from the result
            exclusion_part = part[1:]
            exclusion_pages = parse_simple_part(exclusion_part)
            # Remove exclusion pages from our list
            for page in exclusion_pages:
                while page in pages:
                    pages.remove(page)
        else:
            # Regular range - add to result
            pages.extend(parse_simple_part(part))

    # Apply top-level :odd or :even filter if present
    if filter_type:
        # Note: odd/even refers to POSITIONS (1-indexed), not page numbers
        if filter_type == 'odd':
            pages = [pages[i] for i in range(0, len(pages), 2)]
        else:  # even
            pages = [pages[i] for i in range(1, len(pages), 2)]

    # Validate and convert to 0-indexed
    result = []
    for page in pages:
        if page < 1 or page > total_pages:
            raise ValueError(f"Page {page} out of range (1-{total_pages})")
        result.append(page - 1)

    return result
