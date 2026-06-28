from rest_framework import serializers

from .models import (
    Project,
    ProjectAllocation
)


class ProjectSerializer(serializers.ModelSerializer):

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    headcount = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'name',
            'client',
            'start_date',
            'end_date',
            'status',
            'status_display',
            'description',
            'headcount',
        ]

    def get_headcount(self, obj):
        annotated = getattr(obj, 'active_headcount', None)
        if annotated is not None:
            return annotated
        return obj.projectallocation_set.filter(
            released_on__isnull=True
        ).count()


class ProjectAllocationSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()

    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True
    )

    project_name = serializers.CharField(
        source='project.name',
        read_only=True
    )

    project_status = serializers.CharField(
        source='project.status',
        read_only=True
    )

    is_active = serializers.SerializerMethodField()

    class Meta:
        model = ProjectAllocation
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'project',
            'project_name',
            'project_status',
            'role',
            'responsibilities',
            'notes',
            'allocated_on',
            'released_on',
            'is_active',
        ]

    def get_employee_name(self, obj):
        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return None

    def get_is_active(self, obj):
        return obj.released_on is None


class ProjectAllocationSelfUpdateSerializer(serializers.ModelSerializer):
    """Employee self-service: role, responsibilities, and notes only."""

    class Meta:
        model = ProjectAllocation
        fields = ['role', 'responsibilities', 'notes']

    def validate_role(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Role is required.')
        return value
