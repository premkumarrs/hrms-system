from datetime import date

from django.db.models import Count, Q
from django.db import transaction

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from authentication.permissions import IsHROrReadOnly, get_linked_employee_id
from authentication.audit import log_audit
from authentication.rbac import (
    filter_by_employee_scope,
    filter_projects_for_user,
    user_can_access_employee,
)
from rest_framework.exceptions import PermissionDenied

from .models import (
    Project,
    ProjectAllocation
)

from .serializers import (
    ProjectSerializer,
    ProjectAllocationSerializer,
    ProjectAllocationSelfUpdateSerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsHROrReadOnly]

    filter_backends = [filters.SearchFilter]

    search_fields = ['name', 'client', 'description']

    def get_queryset(self):

        qs = Project.objects.all().order_by('-start_date')

        status_value = self.request.query_params.get('status')
        if status_value:
            qs = qs.filter(status=status_value)

        return filter_projects_for_user(qs, self.request.user).annotate(
            active_headcount=Count(
                'projectallocation',
                filter=Q(projectallocation__released_on__isnull=True),
            )
        )

    @action(detail=False, methods=['get'])
    def headcount(self, request):
        """Active allocation headcount per project."""

        projects = (
            filter_projects_for_user(Project.objects.all(), request.user)
            .annotate(
                active_headcount=Count(
                    'projectallocation',
                    filter=Q(projectallocation__released_on__isnull=True),
                )
            )
            .order_by('-active_headcount', 'name')
        )

        data = [
            {
                "project": project.id,
                "project_name": project.name,
                "client": project.client,
                "status": project.status,
                "headcount": project.active_headcount,
            }
            for project in projects
        ]

        return Response(data)

    @action(detail=True, methods=['get'])
    def allocations(self, request, pk=None):
        """Full allocation history for a single project."""

        project = self.get_object()

        qs = (
            ProjectAllocation.objects
            .select_related('employee', 'project')
            .filter(project=project)
            .order_by('-allocated_on')
        )
        qs = filter_by_employee_scope(qs, request.user)

        serializer = ProjectAllocationSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        """Allocate an employee to this project."""

        project = self.get_object()

        employee_id = request.data.get('employee')
        if not employee_id:
            return Response(
                {"detail": "'employee' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user_can_access_employee(request.user, employee_id):
            return Response(
                {"detail": "You are not authorized to allocate this employee."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = {
            "project": project.id,
            "employee": request.data.get('employee'),
            "role": request.data.get('role', ''),
            "allocated_on": request.data.get(
                'allocated_on',
                date.today().isoformat()
            ),
        }

        serializer = ProjectAllocationSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            allocation = serializer.save()

        log_audit(
            request,
            'project_allocate',
            target=allocation,
            changes={
                'employee_id': allocation.employee_id,
                'project_id': allocation.project_id,
                'role': allocation.role,
            },
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProjectAllocationViewSet(viewsets.ModelViewSet):

    queryset = ProjectAllocation.objects.select_related(
        'employee', 'project'
    ).all()
    serializer_class = ProjectAllocationSerializer
    permission_classes = [IsHROrReadOnly]

    filter_backends = [filters.SearchFilter]

    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
        'project__name',
        'role',
    ]

    def get_permissions(self):
        if self.action == 'self_update':
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):

        qs = (
            ProjectAllocation.objects
            .select_related('employee', 'project')
            .all()
            .order_by('-allocated_on')
        )

        params = self.request.query_params

        employee = params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)

        project = params.get('project')
        if project:
            qs = qs.filter(project_id=project)

        active = params.get('active')
        if active is not None and active != '':
            if active.lower() in ('1', 'true', 'yes'):
                qs = qs.filter(released_on__isnull=True)
            else:
                qs = qs.filter(released_on__isnull=False)

        return filter_by_employee_scope(qs, self.request.user)

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release an employee from a project (ends the allocation)."""

        allocation = self.get_object()

        if allocation.released_on:
            return Response(
                {"detail": "Allocation is already released."},
                status=status.HTTP_400_BAD_REQUEST
            )

        released_on = request.data.get('released_on') or date.today().isoformat()

        allocation.released_on = released_on
        allocation.save()

        return Response(self.get_serializer(allocation).data)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Current (active) allocations for an employee."""

        employee_id = request.query_params.get('employee')

        if not employee_id:
            return Response(
                {"detail": "'employee' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_can_access_employee(request.user, employee_id):
            return Response(
                {"detail": "You are not authorized to view these allocations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = (
            ProjectAllocation.objects
            .select_related('employee', 'project')
            .filter(employee_id=employee_id, released_on__isnull=True)
            .order_by('-allocated_on')
        )

        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Full allocation history (current + previous) for an employee."""

        employee_id = request.query_params.get('employee')

        if not employee_id:
            return Response(
                {"detail": "'employee' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_can_access_employee(request.user, employee_id):
            return Response(
                {"detail": "You are not authorized to view these allocations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = (
            ProjectAllocation.objects
            .select_related('employee', 'project')
            .filter(employee_id=employee_id)
            .order_by('-allocated_on')
        )

        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['patch'], url_path='self-update')
    def self_update(self, request, pk=None):
        """Allow an employee to update role/responsibilities/notes on own active allocation."""

        allocation = self.get_object()
        linked = get_linked_employee_id(request.user)

        if not linked or allocation.employee_id != linked:
            raise PermissionDenied(
                "You may only update your own project assignment details."
            )

        if allocation.released_on:
            return Response(
                {"detail": "Released allocations cannot be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProjectAllocationSelfUpdateSerializer(
            allocation,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(ProjectAllocationSerializer(allocation).data)
