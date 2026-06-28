from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import transaction

from authentication.permissions import IsHROrReadOnly
from authentication.audit import log_audit, snapshot_model
from authentication.rbac import filter_by_employee_scope

from .models import SalaryRecord
from .serializers import SalaryRecordSerializer
from .payslip_pdf import build_payslip_pdf


class SalaryRecordViewSet(viewsets.ModelViewSet):

    queryset = SalaryRecord.objects.select_related('employee').all()
    serializer_class = SalaryRecordSerializer
    permission_classes = [IsHROrReadOnly]

    filter_backends = [filters.SearchFilter]

    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
        'period',
    ]

    def get_queryset(self):
        qs = (
            SalaryRecord.objects
            .select_related('employee')
            .all()
            .order_by('-period')
        )

        params = self.request.query_params

        employee = params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)

        period = params.get('period')
        if period:
            qs = qs.filter(period=period)

        return filter_by_employee_scope(qs, self.request.user)

    def perform_create(self, serializer):
        with transaction.atomic():
            record = serializer.save()
        log_audit(
            self.request,
            'payroll_create',
            target=record,
            changes={'after': snapshot_model(record)},
        )

    def perform_update(self, serializer):
        before = snapshot_model(serializer.instance)
        with transaction.atomic():
            record = serializer.save()
        log_audit(
            self.request,
            'payroll_update',
            target=record,
            changes={
                'before': before,
                'after': snapshot_model(record),
            },
        )

    @action(detail=True, methods=['get'])
    def payslip(self, request, pk=None):
        """Download a payslip PDF for this salary record."""

        record = self.get_object()
        pdf_bytes = build_payslip_pdf(record)
        filename = (
            f"payslip_{record.employee.employee_code}_{record.period}.pdf"
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
