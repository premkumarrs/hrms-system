from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from employees.models import Employee
from attendance.models import Attendance
from leaves.models import Leave
from projects.models import Project
from lifecycle.models import Resignation
from authentication.rbac import (
    filter_by_employee_scope,
    filter_employees_for_user,
    filter_projects_for_user,
)
from config.cycle import cycle_period_label, get_cycle_range
from config.dates import parse_date as _parse_date


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):

    today = date.today()
    cycle_start, cycle_end = get_cycle_range(today)

    employees = filter_employees_for_user(Employee.objects.all(), request.user)
    attendance = filter_by_employee_scope(
        Attendance.objects.all(), request.user
    )
    leaves = filter_by_employee_scope(Leave.objects.all(), request.user)
    projects = filter_projects_for_user(Project.objects.all(), request.user)

    emp_stats = employees.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='ACTIVE')),
    )
    att_today = attendance.filter(date=today).aggregate(
        present=Count('id', filter=Q(status='PRESENT')),
        absent=Count('id', filter=Q(status='ABSENT')),
    )
    cycle_attendance = attendance.filter(date__range=(cycle_start, cycle_end))
    cycle_att_stats = cycle_attendance.aggregate(
        present=Count('id', filter=Q(status='PRESENT')),
    )
    cycle_leaves = leaves.filter(
        start_date__lte=cycle_end,
        end_date__gte=cycle_start,
    )
    on_leave = leaves.filter(
        status='APPROVED',
        start_date__lte=today,
        end_date__gte=today,
    ).count()
    active_projects = projects.filter(status='ACTIVE').count()

    return Response({
        "total_employees": emp_stats['total'],
        "active_employees": emp_stats['active'],
        "present_today": att_today['present'],
        "absent_today": att_today['absent'],
        "on_leave": on_leave,
        "active_projects": active_projects,
        "cycle_start": cycle_start.isoformat(),
        "cycle_end": cycle_end.isoformat(),
        "cycle_period": cycle_period_label(today),
        "cycle_present_days": cycle_att_stats['present'],
        "cycle_leave_requests": cycle_leaves.count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_analytics(request):
    """Trend data for dashboard charts."""

    today = date.today()
    attendance_qs = filter_by_employee_scope(
        Attendance.objects.all(), request.user
    )
    leave_qs = filter_by_employee_scope(Leave.objects.all(), request.user)

    # Attendance trend — last 14 days (present vs absent).
    trend_start = today - timedelta(days=13)
    day_counts = {
        (row['date'], row['status']): row['count']
        for row in attendance_qs.filter(date__range=(trend_start, today))
        .values('date', 'status')
        .annotate(count=Count('id'))
    }
    attendance_trend = []
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        attendance_trend.append({
            "date": day.isoformat(),
            "present": day_counts.get((day, 'PRESENT'), 0),
            "absent": day_counts.get((day, 'ABSENT'), 0),
        })

    # Leave trend — last 6 months.
    six_months_ago = today.replace(day=1) - timedelta(days=150)
    leave_rows = (
        leave_qs
        .filter(start_date__gte=six_months_ago)
        .annotate(month=TruncMonth('start_date'))
        .values('month')
        .annotate(
            approved=Count('id', filter=Q(status='APPROVED')),
            pending=Count('id', filter=Q(status='PENDING')),
            rejected=Count('id', filter=Q(status='REJECTED')),
        )
        .order_by('month')
    )
    leave_trend = [
        {
            "month": row['month'].strftime('%Y-%m'),
            "approved": row['approved'],
            "pending": row['pending'],
            "rejected": row['rejected'],
        }
        for row in leave_rows
    ]

    # Project headcount (active allocations).
    project_headcount = []
    projects = (
        filter_projects_for_user(Project.objects.all(), request.user)
        .annotate(
            headcount=Count(
                'projectallocation',
                filter=Q(projectallocation__released_on__isnull=True)
            )
        )
        .order_by('-headcount', 'name')[:10]
    )
    for project in projects:
        project_headcount.append({
            "project": project.name,
            "headcount": project.headcount,
        })

    # Attrition trend — last 12 months.
    year_ago = today - timedelta(days=365)
    attrition_rows = (
        filter_by_employee_scope(
            Resignation.objects.all(), request.user
        )
        .filter(resignation_date__gte=year_ago)
        .annotate(month=TruncMonth('resignation_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    attrition_trend = [
        {
            "month": row['month'].strftime('%Y-%m'),
            "count": row['count'],
        }
        for row in attrition_rows
    ]

    # Attendance deviation highlights (current cycle).
    from attendance import services as attendance_services

    cycle_start, cycle_end = attendance_services.get_cycle_range()
    deviation_rows = []
    att_rows = (
        attendance_qs
        .filter(date__range=(cycle_start, cycle_end))
        .values(
            'employee__employee_code',
            'employee__first_name',
            'employee__last_name',
        )
        .annotate(
            present=Count('id', filter=Q(status='PRESENT')),
            total_hours=Sum('working_hours'),
        )
        .order_by('employee__employee_code')[:10]
    )
    standard = float(attendance_services.STANDARD_WORK_HOURS)
    for row in att_rows:
        actual = float(row['total_hours'] or 0)
        expected = row['present'] * standard
        deviation_rows.append({
            "employee": (
                f"{row['employee__first_name']} {row['employee__last_name']}".strip()
            ),
            "deviation_hours": round(actual - expected, 2),
        })

    return Response({
        "attendance_trend": attendance_trend,
        "leave_trend": leave_trend,
        "project_headcount": project_headcount,
        "attrition_trend": attrition_trend,
        "attendance_deviation": deviation_rows,
    })


# ----------------------------------------------------------------------
# Reports — each returns {title, columns, rows} for generic table + export.
# ----------------------------------------------------------------------

def _report_response(title, columns, rows):
    return Response({
        "title": title,
        "columns": columns,
        "rows": rows,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_attendance(request):

    qs = filter_by_employee_scope(
        Attendance.objects.select_related('employee').all(),
        request.user,
    ).order_by('-date')

    params = request.query_params

    start = _parse_date(params.get('start'))
    end = _parse_date(params.get('end'))
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)

    search = params.get('search')
    if search:
        qs = qs.filter(
            Q(employee__first_name__icontains=search)
            | Q(employee__last_name__icontains=search)
            | Q(employee__employee_code__icontains=search)
        )

    columns = [
        "Code", "Employee", "Date", "Check In", "Check Out",
        "Hours", "Late", "Status"
    ]

    rows = []
    for a in qs:
        name = f"{a.employee.first_name} {a.employee.last_name}".strip()
        rows.append([
            a.employee.employee_code,
            name,
            str(a.date),
            str(a.check_in)[:5] if a.check_in else "",
            str(a.check_out)[:5] if a.check_out else "",
            str(a.working_hours),
            "Yes" if a.late_entry else "No",
            a.get_status_display(),
        ])

    return _report_response("Attendance Report", columns, rows)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_leave(request):

    qs = filter_by_employee_scope(
        Leave.objects.select_related('employee', 'approved_by').all(),
        request.user,
    ).order_by('-start_date')

    params = request.query_params

    start = _parse_date(params.get('start'))
    end = _parse_date(params.get('end'))

    if not start and not end:
        ref = _parse_date(params.get('date')) or date.today()
        start, end = get_cycle_range(ref)

    if start:
        qs = qs.filter(end_date__gte=start)
    if end:
        qs = qs.filter(start_date__lte=end)

    status_value = params.get('status')
    if status_value:
        qs = qs.filter(status=status_value)

    search = params.get('search')
    if search:
        qs = qs.filter(
            Q(employee__first_name__icontains=search)
            | Q(employee__last_name__icontains=search)
            | Q(employee__employee_code__icontains=search)
        )

    columns = [
        "Code", "Employee", "Type", "Start", "End",
        "Days", "Status", "Approved By"
    ]

    rows = []
    for leave in qs:
        name = f"{leave.employee.first_name} {leave.employee.last_name}".strip()
        approver = ""
        if leave.approved_by:
            approver = (
                f"{leave.approved_by.first_name} "
                f"{leave.approved_by.last_name}"
            ).strip()
        rows.append([
            leave.employee.employee_code,
            name,
            leave.get_leave_type_display(),
            str(leave.start_date),
            str(leave.end_date),
            leave.number_of_days,
            leave.get_status_display(),
            approver or "-",
        ])

    return _report_response("Leave Report", columns, rows)


def _resolve_payroll_period(params):
    """Map request params to a payroll period label (26th–25th cycle end month)."""

    period = params.get('period')
    if period:
        return period

    ref = _parse_date(params.get('date'))
    return cycle_period_label(ref)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_project_headcount(request):

    projects = (
        filter_projects_for_user(Project.objects.all(), request.user)
        .annotate(
            headcount=Count(
                'projectallocation',
                filter=Q(projectallocation__released_on__isnull=True)
            )
        )
        .order_by('-headcount', 'name')
    )

    columns = ["Project", "Client", "Status", "Active Headcount"]

    rows = [
        [p.name, p.client, p.get_status_display(), p.headcount]
        for p in projects
    ]

    return _report_response("Project Headcount Report", columns, rows)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_attrition(request):

    qs = filter_by_employee_scope(
        Resignation.objects.select_related('employee').all(),
        request.user,
    ).order_by('-resignation_date')

    year = request.query_params.get('year')
    if year and year.isdigit():
        qs = qs.filter(resignation_date__year=int(year))

    columns = [
        "Code", "Employee", "Resignation Date",
        "Last Working Day", "Exit Status", "Settlement"
    ]

    rows = []
    for r in qs:
        name = f"{r.employee.first_name} {r.employee.last_name}".strip()
        rows.append([
            r.employee.employee_code,
            name,
            str(r.resignation_date),
            str(r.last_working_day) if r.last_working_day else "-",
            r.get_exit_status_display(),
            r.get_final_settlement_status_display(),
        ])

    return _report_response("Attrition Report", columns, rows)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_payroll(request):

    from payroll.models import SalaryRecord

    qs = filter_by_employee_scope(
        SalaryRecord.objects.select_related('employee').all(),
        request.user,
    ).order_by('-period', 'employee__employee_code')

    period = _resolve_payroll_period(request.query_params)
    qs = qs.filter(period=period)

    cycle_start, cycle_end = get_cycle_range(
        _parse_date(request.query_params.get('date'))
    )

    columns = [
        "Code", "Employee", "Period", "Basic",
        "Allowances", "Deductions", "Net Salary"
    ]

    rows = []
    for record in qs:
        name = f"{record.employee.first_name} {record.employee.last_name}".strip()
        rows.append([
            record.employee.employee_code,
            name,
            record.period,
            str(record.basic_salary),
            str(record.allowances),
            str(record.deductions),
            str(record.net_salary),
        ])

    return _report_response(
        f"Payroll Summary ({cycle_start} to {cycle_end})",
        columns,
        rows,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_insights(request):
    """Pending approvals, upcoming events, and recent notifications."""

    from authentication.permissions import ROLE_HR, ROLE_MANAGER, get_role
    from notifications.models import Notification
    from notifications.services import _pending_counts_for_manager

    from .insights import upcoming_anniversaries, upcoming_birthdays

    today = date.today()
    employees = filter_employees_for_user(Employee.objects.all(), request.user)
    role = get_role(request.user)

    pending_leaves = 0
    pending_permissions = 0
    if role in (ROLE_HR, ROLE_MANAGER):
        pending_leaves, pending_permissions = _pending_counts_for_manager(
            request.user
        )

    notifications_qs = Notification.objects.filter(
        Q(recipient=request.user) | Q(recipient__isnull=True)
    ).select_related('employee').order_by('-created_at')[:8]

    recent_notifications = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
            "employee_name": (
                f"{n.employee.first_name} {n.employee.last_name}".strip()
                if n.employee else ""
            ),
        }
        for n in notifications_qs
    ]

    return Response({
        "pending_leaves": pending_leaves,
        "pending_permissions": pending_permissions,
        "upcoming_birthdays": upcoming_birthdays(employees, today),
        "upcoming_anniversaries": upcoming_anniversaries(employees, today),
        "recent_notifications": recent_notifications,
    })
