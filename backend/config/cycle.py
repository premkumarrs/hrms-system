"""Shared payroll/attendance cycle (26th of month → 25th of next month)."""

from datetime import date


CYCLE_START_DAY = 26
CYCLE_END_DAY = 25


def _first_of_month(d):
    return date(d.year, d.month, 1)


def _add_months(d, delta):
    index = (d.year * 12 + (d.month - 1)) + delta
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


def get_cycle_range(ref_date=None):
    """Return (start, end) for the cycle containing ``ref_date``."""

    if ref_date is None:
        ref_date = date.today()

    if ref_date.day >= CYCLE_START_DAY:
        start_month = _first_of_month(ref_date)
        end_month = _add_months(start_month, 1)
    else:
        end_month = _first_of_month(ref_date)
        start_month = _add_months(end_month, -1)

    start = start_month.replace(day=CYCLE_START_DAY)
    end = end_month.replace(day=CYCLE_END_DAY)
    return start, end


def cycle_period_label(ref_date=None):
    """Payroll period key for a cycle: YYYY-MM of the cycle end month (25th).

    Existing ``SalaryRecord.period`` values use this label. No data migration
    required — reports filter by this key for the active cycle.
    """

    _, end = get_cycle_range(ref_date)
    return f"{end.year}-{end.month:02d}"
