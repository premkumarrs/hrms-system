from datetime import datetime, date

from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from authentication.permissions import (
    IsHROrManagerOrReadOnly,
    get_role,
    get_linked_employee_id,
    ROLE_HR,
    ROLE_MANAGER,
)
from authentication.rbac import filter_by_employee_scope, user_can_access_employee

from employees.models import Employee

from config.dates import parse_date as _parse_date

from .models import Attendance
from .serializers import AttendanceSerializer
from . import services


class AttendanceViewSet(viewsets.ModelViewSet):

    # Base queryset (router uses it for basename); get_queryset() applies filters.
    queryset = Attendance.objects.select_related('employee').all()

    serializer_class = AttendanceSerializer

    filter_backends = [filters.SearchFilter]

    def get_permissions(self):
        # Check-in/out: any authenticated user (self-only enforced in action).
        if self.action in ('check_in', 'check_out'):
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]

        from rest_framework.permissions import IsAuthenticated
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated()]

        return [IsAuthenticated(), IsHROrManagerOrReadOnly()]

    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    ]

    def get_queryset(self):

        qs = (
            Attendance.objects
            .select_related('employee')
            .all()
            .order_by('-date', 'employee__employee_code')
        )

        params = self.request.query_params

        employee = params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)

        single_date = params.get('date')
        if single_date:
            qs = qs.filter(date=single_date)

        start = _parse_date(params.get('start'))
        end = _parse_date(params.get('end'))

        if start and end:
            qs = qs.filter(date__range=(start, end))
        elif start:
            qs = qs.filter(date__gte=start)
        elif end:
            qs = qs.filter(date__lte=end)

        status_value = params.get('status')
        if status_value:
            qs = qs.filter(status=status_value)

        late = params.get('late_entry')
        if late is not None and late != '':
            qs = qs.filter(late_entry=late.lower() in ('1', 'true', 'yes'))

        return filter_by_employee_scope(qs, self.request.user)

    # ------------------------------------------------------------------
    # Derived-value handling for manual create / edit
    # ------------------------------------------------------------------

    def perform_create(self, serializer):
        instance = serializer.save()
        self._apply_derived_values(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._apply_derived_values(instance)

    def _apply_derived_values(self, instance):
        """Recompute objective fields (late flag + working hours) from times."""

        instance.late_entry = services.is_late(instance.check_in)

        if instance.check_in and instance.check_out:
            instance.working_hours = services.calculate_working_hours(
                instance.check_in,
                instance.check_out,
                instance.date
            )

        instance.save(update_fields=['late_entry', 'working_hours'])

    # ------------------------------------------------------------------
    # Check In / Check Out
    # ------------------------------------------------------------------

    @action(detail=False, methods=['post'], url_path='check-in')
    def check_in(self, request):

        employee = self._get_employee(request)
        if isinstance(employee, Response):
            return employee

        denied = self._assert_check_in_out_allowed(request, employee)
        if denied:
            return denied

        today = date.today()

        record = Attendance.objects.filter(
            employee=employee,
            date=today
        ).first()

        if record and record.check_in:
            return Response(
                {"detail": "Employee has already checked in today."},
                status=status.HTTP_400_BAD_REQUEST
            )

        now_time = datetime.now().time()

        if record is None:
            record = Attendance(employee=employee, date=today)

        record.check_in = now_time
        record.late_entry = services.is_late(now_time)
        record.status = 'PRESENT'
        record.save()

        return Response(
            AttendanceSerializer(record).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'], url_path='check-out')
    def check_out(self, request):

        employee = self._get_employee(request)
        if isinstance(employee, Response):
            return employee

        denied = self._assert_check_in_out_allowed(request, employee)
        if denied:
            return denied

        today = date.today()

        record = Attendance.objects.filter(
            employee=employee,
            date=today
        ).first()

        if record is None or not record.check_in:
            return Response(
                {"detail": "No check-in found for today."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if record.check_out:
            return Response(
                {"detail": "Employee has already checked out today."},
                status=status.HTTP_400_BAD_REQUEST
            )

        now_time = datetime.now().time()

        record.check_out = now_time
        record.working_hours = services.calculate_working_hours(
            record.check_in,
            now_time,
            today
        )
        record.status = services.derive_status(record.working_hours)
        record.save()

        return Response(AttendanceSerializer(record).data)

    def _get_employee(self, request):
        """Resolve the employee from request data or return an error Response."""

        employee_id = request.data.get('employee')

        if not employee_id:
            return Response(
                {"detail": "'employee' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return get_object_or_404(Employee, pk=employee_id)

    def _assert_check_in_out_allowed(self, request, employee):
        """Employees may only check in/out for their own linked record."""

        role = get_role(request.user)
        if role in (ROLE_HR, ROLE_MANAGER):
            return None

        linked = get_linked_employee_id(request.user)
        if linked and linked == employee.id:
            return None

        return Response(
            {"detail": "You may only check in/out for your own employee record."},
            status=status.HTTP_403_FORBIDDEN
        )

    # ------------------------------------------------------------------
    # Summary / Reports / History
    # ------------------------------------------------------------------

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Cycle summary for one employee (or everyone in scope)."""

        start, end = self._resolve_cycle(request)

        qs = filter_by_employee_scope(
            Attendance.objects.filter(date__range=(start, end)),
            request.user,
        )

        employee_id = request.query_params.get('employee')
        if employee_id:
            if not user_can_access_employee(request.user, employee_id):
                return Response(
                    {"detail": "You are not authorized to view this summary."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            qs = qs.filter(employee_id=employee_id)

        counts = qs.aggregate(
            present=Count('id', filter=Q(status='PRESENT')),
            absent=Count('id', filter=Q(status='ABSENT')),
            half_day=Count('id', filter=Q(status='HALF_DAY')),
            leave=Count('id', filter=Q(status='LEAVE')),
            late=Count('id', filter=Q(late_entry=True)),
            total_hours=Sum('working_hours'),
        )

        total_hours = counts['total_hours'] or 0
        present_days = counts['present'] or 0

        average = 0
        if present_days:
            average = round(float(total_hours) / present_days, 2)

        return Response({
            "cycle_start": start.isoformat(),
            "cycle_end": end.isoformat(),
            "present": present_days,
            "absent": counts['absent'] or 0,
            "half_day": counts['half_day'] or 0,
            "leave": counts['leave'] or 0,
            "late_count": counts['late'] or 0,
            "total_working_hours": float(total_hours),
            "average_working_hours": average,
        })

    @action(detail=False, methods=['get'])
    def report(self, request):
        """Per-employee monthly (cycle) report with hours deviation."""

        start, end = self._resolve_cycle(request)

        base_qs = filter_by_employee_scope(
            Attendance.objects.filter(date__range=(start, end)),
            request.user,
        )

        employee_id = request.query_params.get('employee')
        if employee_id:
            if not user_can_access_employee(request.user, employee_id):
                return Response(
                    {"detail": "You are not authorized to view this report."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            base_qs = base_qs.filter(employee_id=employee_id)

        qs = (
            base_qs
            .values('employee', 'employee__employee_code',
                    'employee__first_name', 'employee__last_name')
            .annotate(
                present=Count('id', filter=Q(status='PRESENT')),
                absent=Count('id', filter=Q(status='ABSENT')),
                half_day=Count('id', filter=Q(status='HALF_DAY')),
                leave=Count('id', filter=Q(status='LEAVE')),
                late=Count('id', filter=Q(late_entry=True)),
                total_hours=Sum('working_hours'),
            )
            .order_by('employee__employee_code')
        )

        standard = float(services.STANDARD_WORK_HOURS)
        half = float(services.HALF_DAY_HOURS)

        rows = []
        for row in qs:
            actual = float(row['total_hours'] or 0)
            expected = row['present'] * standard + row['half_day'] * half
            deviation = round(actual - expected, 2)

            name = (
                f"{row['employee__first_name']} "
                f"{row['employee__last_name']}"
            ).strip()

            rows.append({
                "employee": row['employee'],
                "employee_code": row['employee__employee_code'],
                "employee_name": name,
                "present": row['present'],
                "absent": row['absent'],
                "half_day": row['half_day'],
                "leave": row['leave'],
                "late_count": row['late'],
                "expected_hours": round(expected, 2),
                "actual_hours": round(actual, 2),
                "deviation_hours": deviation,
            })

        return Response({
            "cycle_start": start.isoformat(),
            "cycle_end": end.isoformat(),
            "results": rows,
        })

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Full attendance history for a single employee (optionally a cycle)."""

        employee_id = request.query_params.get('employee')

        if not employee_id:
            return Response(
                {"detail": "'employee' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_can_access_employee(request.user, employee_id):
            return Response(
                {"detail": "You are not authorized to view this history."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = (
            Attendance.objects
            .select_related('employee')
            .filter(employee_id=employee_id)
            .order_by('-date')
        )

        start = _parse_date(request.query_params.get('start'))
        end = _parse_date(request.query_params.get('end'))

        if start and end:
            qs = qs.filter(date__range=(start, end))

        serializer = AttendanceSerializer(qs, many=True)
        return Response(serializer.data)

    def _resolve_cycle(self, request):
        """Resolve the cycle range from explicit start/end or a reference date."""

        start = _parse_date(request.query_params.get('start'))
        end = _parse_date(request.query_params.get('end'))

        if start and end:
            return start, end

        ref = _parse_date(request.query_params.get('date'))
        return services.get_cycle_range(ref)
