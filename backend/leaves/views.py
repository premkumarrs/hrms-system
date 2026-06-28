from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from employees.models import Employee
from authentication.audit import log_audit
from authentication.permissions import IsManagerOrHR
from authentication.rbac import (
    filter_by_employee_scope,
    user_can_access_employee,
)

from config.dates import parse_date as _parse_date

from .models import Leave, Permission
from .serializers import LeaveSerializer, PermissionSerializer
from . import services


class _ApprovalMixin:
    """Shared approve / reject actions for request-style models."""

    def get_permissions(self):
        # Only Managers and HR may approve or reject requests.
        if self.action in ('approve', 'reject'):
            return [IsAuthenticated(), IsManagerOrHR()]
        return [IsAuthenticated()]

    def _set_decision(self, request, new_status):
        obj = self.get_object()

        if not user_can_access_employee(request.user, obj.employee_id):
            return Response(
                {"detail": "You are not authorized to act on this request."},
                status=status.HTTP_403_FORBIDDEN
            )

        if new_status == 'APPROVED' and hasattr(obj, 'leave_type'):
            ok, message = services.validate_leave_balance(
                obj.employee,
                obj.leave_type,
                obj.start_date,
                obj.end_date,
                exclude_leave_id=obj.pk,
            )
            if not ok:
                return Response(
                    {"detail": message},
                    status=status.HTTP_400_BAD_REQUEST
                )

        obj.status = new_status

        approver = request.data.get('approved_by')
        if approver:
            obj.approved_by_id = approver

        with transaction.atomic():
            obj.save()

        if hasattr(obj, 'leave_type'):
            action_name = (
                'leave_approved' if new_status == 'APPROVED'
                else 'leave_rejected'
            )
        else:
            action_name = (
                'permission_approved' if new_status == 'APPROVED'
                else 'permission_rejected'
            )

        log_audit(
            request,
            action_name,
            target=obj,
            changes={'status': new_status},
        )

        self._post_decision(obj, new_status)

        return Response(self.get_serializer(obj).data)

    def _post_decision(self, obj, new_status):
        """Hook for subclasses to react to an approve/reject decision."""
        return None

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._set_decision(request, 'APPROVED')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._set_decision(request, 'REJECTED')


class LeaveViewSet(_ApprovalMixin, viewsets.ModelViewSet):

    queryset = Leave.objects.select_related('employee', 'approved_by').all()
    serializer_class = LeaveSerializer
    permission_classes = [IsAuthenticated]

    def _post_decision(self, obj, new_status):
        # Notify the employee of the leave decision (best-effort).
        try:
            from notifications.services import notify_leave_decision
            notify_leave_decision(obj, approved=(new_status == 'APPROVED'))
        except Exception:
            pass

    filter_backends = [filters.SearchFilter]

    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
        'reason',
    ]

    def get_queryset(self):

        qs = (
            Leave.objects
            .select_related('employee', 'approved_by')
            .all()
            .order_by('-created_at')
        )

        params = self.request.query_params

        employee = params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)

        status_value = params.get('status')
        if status_value:
            qs = qs.filter(status=status_value)

        leave_type = params.get('leave_type')
        if leave_type:
            qs = qs.filter(leave_type=leave_type)

        start = _parse_date(params.get('start'))
        end = _parse_date(params.get('end'))

        if start:
            qs = qs.filter(start_date__gte=start)
        if end:
            qs = qs.filter(end_date__lte=end)

        return filter_by_employee_scope(qs, self.request.user)

    def perform_create(self, serializer):
        employee = serializer.validated_data['employee']
        if not user_can_access_employee(self.request.user, employee.id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "You may only create leave requests for employees in your scope."
            )
        serializer.save()

    def perform_update(self, serializer):
        employee = serializer.validated_data.get(
            'employee', serializer.instance.employee
        )
        if not user_can_access_employee(self.request.user, employee.id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "You may only update leave requests for employees in your scope."
            )
        serializer.save()

    @action(detail=False, methods=['get'])
    def history(self, request):
        employee_id = request.query_params.get('employee')

        if not employee_id:
            return Response(
                {"detail": "'employee' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_can_access_employee(request.user, employee_id):
            return Response(
                {"detail": "You are not authorized to view this leave history."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = (
            Leave.objects
            .select_related('employee', 'approved_by')
            .filter(employee_id=employee_id)
            .order_by('-start_date')
        )

        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def balance(self, request):
        employee_id = request.query_params.get('employee')

        if not employee_id:
            return Response(
                {"detail": "'employee' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_can_access_employee(request.user, employee_id):
            return Response(
                {"detail": "You are not authorized to view this leave balance."},
                status=status.HTTP_403_FORBIDDEN,
            )

        employee = get_object_or_404(Employee, pk=employee_id)

        year = request.query_params.get('year')
        year = int(year) if year and year.isdigit() else None

        return Response(services.compute_balances(employee, year))


class PermissionViewSet(_ApprovalMixin, viewsets.ModelViewSet):

    queryset = Permission.objects.select_related(
        'employee', 'approved_by'
    ).all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]

    def _post_decision(self, obj, new_status):
        try:
            from notifications.services import notify_permission_decision
            notify_permission_decision(obj, approved=(new_status == 'APPROVED'))
        except Exception:
            pass

    filter_backends = [filters.SearchFilter]

    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
        'reason',
    ]

    def get_queryset(self):

        qs = (
            Permission.objects
            .select_related('employee', 'approved_by')
            .all()
            .order_by('-date')
        )

        params = self.request.query_params

        employee = params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)

        status_value = params.get('status')
        if status_value:
            qs = qs.filter(status=status_value)

        single_date = params.get('date')
        if single_date:
            qs = qs.filter(date=single_date)

        return filter_by_employee_scope(qs, self.request.user)

    def perform_create(self, serializer):
        employee = serializer.validated_data['employee']
        if not user_can_access_employee(self.request.user, employee.id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "You may only create permission requests in your scope."
            )
        serializer.save()
