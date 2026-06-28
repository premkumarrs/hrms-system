from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse

from authentication.permissions import IsHROrReadOnly
from authentication.rbac import filter_by_employee_scope, user_can_access_employee
from rest_framework.exceptions import PermissionDenied

from .models import Onboarding, Resignation
from .serializers import OnboardingSerializer, ResignationSerializer
from .joining_letter import build_joining_letter_pdf
from .onboarding_checklist import sync_onboarding_document_status


class OnboardingViewSet(viewsets.ModelViewSet):

    queryset = Onboarding.objects.select_related('employee').all()
    serializer_class = OnboardingSerializer
    permission_classes = [IsHROrReadOnly]

    filter_backends = [filters.SearchFilter]

    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    ]

    def get_queryset(self):

        qs = (
            Onboarding.objects
            .select_related('employee')
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

        return filter_by_employee_scope(qs, self.request.user)

    def perform_create(self, serializer):
        employee = serializer.validated_data['employee']
        if not user_can_access_employee(self.request.user, employee.id):
            raise PermissionDenied(
                "You are not authorized to manage onboarding for this employee."
            )
        serializer.save()

    def perform_update(self, serializer):
        employee = serializer.validated_data.get(
            'employee', serializer.instance.employee
        )
        if not user_can_access_employee(self.request.user, employee.id):
            raise PermissionDenied(
                "You are not authorized to manage onboarding for this employee."
            )
        serializer.save()

    @action(detail=True, methods=['get'], url_path='joining-letter')
    def joining_letter(self, request, pk=None):
        """Download a joining letter PDF for this onboarding record."""

        onboarding = self.get_object()
        pdf_bytes = build_joining_letter_pdf(onboarding)
        code = onboarding.employee.employee_code
        filename = f"joining_letter_{code}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='document-checklist')
    def document_checklist(self, request, pk=None):
        """Required onboarding documents with upload status and completion."""

        onboarding = self.get_object()
        checklist = sync_onboarding_document_status(onboarding)
        onboarding.refresh_from_db()

        return Response({
            **checklist,
            'documents_submitted': onboarding.documents_submitted,
            'onboarding_status': onboarding.status,
        })


class ResignationViewSet(viewsets.ModelViewSet):

    queryset = Resignation.objects.select_related('employee').all()
    serializer_class = ResignationSerializer
    permission_classes = [IsHROrReadOnly]

    filter_backends = [filters.SearchFilter]

    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
        'reason',
    ]

    def get_queryset(self):

        qs = (
            Resignation.objects
            .select_related('employee')
            .all()
            .order_by('-resignation_date')
        )

        params = self.request.query_params

        employee = params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)

        exit_status = params.get('exit_status')
        if exit_status:
            qs = qs.filter(exit_status=exit_status)

        settlement = params.get('final_settlement_status')
        if settlement:
            qs = qs.filter(final_settlement_status=settlement)

        return filter_by_employee_scope(qs, self.request.user)

    def perform_create(self, serializer):
        employee = serializer.validated_data['employee']
        if not user_can_access_employee(self.request.user, employee.id):
            raise PermissionDenied(
                "You are not authorized to manage exit records for this employee."
            )
        serializer.save()

    def perform_update(self, serializer):
        employee = serializer.validated_data.get(
            'employee', serializer.instance.employee
        )
        if not user_can_access_employee(self.request.user, employee.id):
            raise PermissionDenied(
                "You are not authorized to manage exit records for this employee."
            )
        serializer.save()
