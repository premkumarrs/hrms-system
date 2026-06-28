"""Leave business rules: annual allocations and balance computation."""

from datetime import date


# Annual leave allocation per leave type (per calendar year).
LEAVE_ALLOCATION = {
    'CL': 12,   # Casual Leave
    'SL': 12,   # Sick Leave
    'EL': 15,   # Earned Leave
}


def leave_days(start_date, end_date):
    """Inclusive number of days covered by a leave request."""

    if not start_date or not end_date:
        return 0

    return (end_date - start_date).days + 1


def _consumed_days(queryset, leave_type):
    consumed = 0
    for leave in queryset.filter(leave_type=leave_type):
        consumed += leave_days(leave.start_date, leave.end_date)
    return consumed


def compute_balances(employee, year=None, exclude_leave_id=None):
    """Return allocated / used / pending / available balance per leave type.

    ``used`` counts APPROVED leaves; ``pending`` counts PENDING requests.
    ``available`` = allocated - used - pending (reserves in-flight requests).
    """

    from .models import Leave

    if year is None:
        year = date.today().year

    base = Leave.objects.filter(
        employee=employee,
        start_date__year=year,
    )

    approved = base.filter(status='APPROVED')
    pending_qs = base.filter(status='PENDING')
    if exclude_leave_id:
        pending_qs = pending_qs.exclude(pk=exclude_leave_id)

    type_labels = dict(Leave.LEAVE_TYPES)

    balances = []

    for code, allocated in LEAVE_ALLOCATION.items():
        used = _consumed_days(approved, code)
        pending = _consumed_days(pending_qs, code)
        available = allocated - used - pending
        balances.append({
            "leave_type": code,
            "leave_type_display": type_labels.get(code, code),
            "allocated": allocated,
            "used": used,
            "pending": pending,
            "available": available,
        })

    return {
        "year": year,
        "balances": balances,
    }


def validate_leave_balance(
    employee, leave_type, start_date, end_date, exclude_leave_id=None
):
    """Return (ok, message) — reject when requested days exceed available balance."""

    if not employee or not leave_type or not start_date or not end_date:
        return True, None

    requested = leave_days(start_date, end_date)
    if requested <= 0:
        return False, "Leave must span at least one day."

    data = compute_balances(
        employee, start_date.year, exclude_leave_id=exclude_leave_id
    )

    for entry in data["balances"]:
        if entry["leave_type"] == leave_type:
            available = entry["available"]
            if requested > available:
                pending_note = ""
                if entry["pending"]:
                    pending_note = (
                        f" ({entry['pending']} day(s) already reserved by "
                        "pending requests)"
                    )
                return False, (
                    f"Insufficient {entry['leave_type_display']} balance. "
                    f"Requested {requested} day(s); "
                    f"{available} day(s) remaining{pending_note}."
                )
            return True, None

    return False, f"Unknown leave type: {leave_type}"
