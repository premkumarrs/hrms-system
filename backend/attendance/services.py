"""Attendance business rules.

Centralises working-hours calculation and late-reporting detection.
Cycle calendar is shared with payroll via ``config.cycle``.
"""

from datetime import datetime, date, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from config.cycle import (
    CYCLE_END_DAY,
    CYCLE_START_DAY,
    get_cycle_range,
)

# Re-export for backward compatibility.
__all__ = [
    'SHIFT_START',
    'GRACE_MINUTES',
    'STANDARD_WORK_HOURS',
    'HALF_DAY_HOURS',
    'CYCLE_START_DAY',
    'CYCLE_END_DAY',
    'get_cycle_range',
    'is_late',
    'calculate_working_hours',
    'derive_status',
]


# --- Configurable business rules -------------------------------------------

# Standard shift start time and grace window for late detection.
SHIFT_START = time(9, 30)
GRACE_MINUTES = 10

# Hours thresholds used to derive a status from worked time.
STANDARD_WORK_HOURS = Decimal("8.00")
HALF_DAY_HOURS = Decimal("4.00")

def is_late(check_in):
    """True if ``check_in`` is later than the shift start plus grace period."""

    if not check_in:
        return False

    cutoff = (
        datetime.combine(date.today(), SHIFT_START)
        + timedelta(minutes=GRACE_MINUTES)
    ).time()

    return check_in > cutoff


def calculate_working_hours(check_in, check_out, work_date=None):
    """Return decimal hours between ``check_in`` and ``check_out``.

    Handles overnight shifts (check-out past midnight) by rolling the
    check-out into the next day.
    """

    if not check_in or not check_out:
        return Decimal("0.00")

    base = work_date or date.today()

    start_dt = datetime.combine(base, check_in)
    end_dt = datetime.combine(base, check_out)

    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    seconds = (end_dt - start_dt).total_seconds()

    hours = Decimal(seconds) / Decimal(3600)

    return hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def derive_status(working_hours):
    """Map worked hours to an attendance status."""

    if working_hours is None or working_hours <= 0:
        return "ABSENT"

    if working_hours < HALF_DAY_HOURS:
        return "HALF_DAY"

    return "PRESENT"
