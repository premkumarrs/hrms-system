import os

from django.http import FileResponse, Http404
from django.db import transaction

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from authentication.permissions import IsHROrReadOnly
from authentication.audit import log_audit
from authentication.rbac import filter_by_employee_scope, user_can_access_employee
from rest_framework.exceptions import PermissionDenied
from employees.models import Employee

from .models import DocumentCategory, EmployeeDocument
from .serializers import (
    DocumentCategorySerializer,
    EmployeeDocumentSerializer
)
from . import letter_service


class DocumentCategoryViewSet(viewsets.ModelViewSet):

    queryset = DocumentCategory.objects.all().order_by('name')
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsHROrReadOnly]


class EmployeeDocumentViewSet(viewsets.ModelViewSet):

    queryset = EmployeeDocument.objects.select_related(
        'employee', 'category'
    ).all()
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [IsHROrReadOnly]

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    filter_backends = [filters.SearchFilter]

    search_fields = [
        'title',
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    ]

    def get_queryset(self):

        qs = (
            EmployeeDocument.objects
            .select_related('employee', 'category')
            .all()
            .order_by('-uploaded_at')
        )

        params = self.request.query_params

        employee = params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)

        category = params.get('category')
        if category:
            qs = qs.filter(category_id=category)

        return filter_by_employee_scope(qs, self.request.user)

    def perform_create(self, serializer):
        employee = serializer.validated_data['employee']
        if not user_can_access_employee(self.request.user, employee.id):
            raise PermissionDenied(
                "You are not authorized to upload documents for this employee."
            )
        with transaction.atomic():
            document = serializer.save()
        log_audit(
            self.request,
            'document_upload',
            target=document,
            changes={'title': document.title, 'category_id': document.category_id},
        )

        try:
            from lifecycle.models import Onboarding
            from lifecycle.onboarding_checklist import sync_onboarding_document_status

            onboarding = Onboarding.objects.filter(
                employee=document.employee
            ).first()
            if onboarding:
                sync_onboarding_document_status(onboarding)
        except Exception:
            pass

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):

        document = self.get_object()

        if not document.file:
            raise Http404("No file attached to this document.")

        return FileResponse(
            document.file.open('rb'),
            as_attachment=True,
            filename=os.path.basename(document.file.name)
        )

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate an HR letter PDF and store it as an employee document."""

        employee_id = request.data.get('employee')
        letter_type = (request.data.get('letter_type') or '').strip().lower()

        if not employee_id:
            return Response(
                {"detail": "'employee' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if letter_type not in letter_service.LETTER_TYPES:
            return Response(
                {
                    "detail": (
                        "Invalid letter_type. Choose from: "
                        + ", ".join(sorted(letter_service.LETTER_TYPES))
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user_can_access_employee(request.user, employee_id):
            return Response(
                {"detail": "You are not authorized to generate documents for this employee."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            employee = Employee.objects.get(pk=employee_id)
        except Employee.DoesNotExist:
            return Response(
                {"detail": "Employee not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            document = letter_service.generate_letter_document(
                employee,
                letter_type,
                notes=request.data.get('notes', ''),
                new_designation=request.data.get('new_designation', ''),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_audit(
            request,
            'document_generate',
            target=document,
            changes={'letter_type': letter_type},
        )

        serializer = self.get_serializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
