"""Shared date parsing helpers."""

from datetime import datetime


def parse_date(value):
    """Parse ``YYYY-MM-DD`` strings; return None on empty or invalid input."""

    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
