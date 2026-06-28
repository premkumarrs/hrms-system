"""Dashboard insight helpers (upcoming events, pending approvals)."""

from datetime import date, timedelta


def _next_occurrence(ref_date, month, day):
    """Return the next calendar date for month/day on or after ref_date."""

    for year in (ref_date.year, ref_date.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate >= ref_date:
            return candidate
    return None


def upcoming_birthdays(employees_qs, today=None, within_days=14, limit=10):
    today = today or date.today()
    end = today + timedelta(days=within_days)
    rows = []
    for emp in employees_qs.filter(status='ACTIVE', date_of_birth__isnull=False):
        nxt = _next_occurrence(today, emp.date_of_birth.month, emp.date_of_birth.day)
        if nxt and nxt <= end:
            rows.append({
                "employee": f"{emp.first_name} {emp.last_name}".strip(),
                "employee_code": emp.employee_code,
                "date": nxt.isoformat(),
            })
    rows.sort(key=lambda row: row["date"])
    return rows[:limit]


def upcoming_anniversaries(employees_qs, today=None, within_days=14, limit=10):
    today = today or date.today()
    end = today + timedelta(days=within_days)
    rows = []
    for emp in employees_qs.filter(status='ACTIVE'):
        nxt = _next_occurrence(today, emp.joining_date.month, emp.joining_date.day)
        if nxt and nxt <= end and emp.joining_date < today:
            years = nxt.year - emp.joining_date.year
            rows.append({
                "employee": f"{emp.first_name} {emp.last_name}".strip(),
                "employee_code": emp.employee_code,
                "date": nxt.isoformat(),
                "years": years,
            })
    rows.sort(key=lambda row: row["date"])
    return rows[:limit]
