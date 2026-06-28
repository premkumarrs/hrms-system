from rest_framework import viewsets, filters
from rest_framework.exceptions import PermissionDenied
from django.db import transaction

from authentication.audit import log_audit, snapshot_model
from authentication.permissions import IsHROrReadOnly
from authentication.rbac import (
    filter_by_employee_scope,
    filter_employees_for_user,
    user_can_access_employee,
)

from .models import (
    Department,
    Designation,
    Employee,
    Education,
    BankDetails,
    IDProof,
    EmergencyContact
)

from .serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeSerializer,
    EducationSerializer,
    BankDetailsSerializer,
    IDProofSerializer,
    EmergencyContactSerializer
)


class DepartmentViewSet(viewsets.ModelViewSet):

    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer
    permission_classes = [IsHROrReadOnly]

    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class DesignationViewSet(viewsets.ModelViewSet):

    queryset = Designation.objects.all().order_by('title')
    serializer_class = DesignationSerializer
    permission_classes = [IsHROrReadOnly]

    filter_backends = [filters.SearchFilter]
    search_fields = ['title']


class EmployeeViewSet(viewsets.ModelViewSet):

    queryset = Employee.objects.all().order_by('employee_code')
    serializer_class = EmployeeSerializer
    permission_classes = [IsHROrReadOnly]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        'first_name',
        'last_name',
        'email',
        'employee_code',
        'phone',
    ]

    ordering_fields = [
        'employee_code',
        'first_name',
        'last_name',
        'joining_date',
        'status',
    ]

    def get_queryset(self):

        qs = (
            Employee.objects
            .select_related('department', 'designation', 'manager')
            .order_by('employee_code')
        )

        params = self.request.query_params

        department = params.get('department')
        if department:
            qs = qs.filter(department_id=department)

        status_value = params.get('status')
        if status_value:
            qs = qs.filter(status=status_value)

        branch = params.get('branch')
        if branch:
            qs = qs.filter(branch=branch)

        return filter_employees_for_user(qs, self.request.user)

    def perform_create(self, serializer):
        with transaction.atomic():
            employee = serializer.save()
            log_audit(
                self.request,
                'employee_create',
                target=employee,
                changes={'after': snapshot_model(employee)},
            )

    def perform_update(self, serializer):
        before = snapshot_model(serializer.instance)
        with transaction.atomic():
            employee = serializer.save()
            log_audit(
                self.request,
                'employee_update',
                target=employee,
                changes={
                    'before': before,
                    'after': snapshot_model(employee),
                },
            )


class _EmployeeChildViewSet(viewsets.ModelViewSet):
    """Base viewset for per-employee detail records (filterable by employee)."""

    permission_classes = [IsHROrReadOnly]

    def get_queryset(self):
        qs = self.queryset
        employee = self.request.query_params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)
        return filter_by_employee_scope(qs, self.request.user)

    def _assert_employee_scope(self, employee):
        if not user_can_access_employee(self.request.user, employee.id):
            raise PermissionDenied(
                "You are not authorized to access this employee's records."
            )

    def perform_create(self, serializer):
        self._assert_employee_scope(serializer.validated_data['employee'])
        serializer.save()

    def perform_update(self, serializer):
        employee = serializer.validated_data.get(
            'employee', serializer.instance.employee
        )
        self._assert_employee_scope(employee)
        serializer.save()


class EducationViewSet(_EmployeeChildViewSet):
    queryset = Education.objects.select_related('employee').all()
    serializer_class = EducationSerializer


class BankDetailsViewSet(_EmployeeChildViewSet):
    queryset = BankDetails.objects.select_related('employee').all()
    serializer_class = BankDetailsSerializer


class IDProofViewSet(_EmployeeChildViewSet):
    queryset = IDProof.objects.select_related('employee').all()
    serializer_class = IDProofSerializer


class EmergencyContactViewSet(_EmployeeChildViewSet):
    queryset = EmergencyContact.objects.select_related('employee').all()
    serializer_class = EmergencyContactSerializer