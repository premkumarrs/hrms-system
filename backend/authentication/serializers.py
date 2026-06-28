from rest_framework import serializers

from employees.models import Employee


class SelfProfileSerializer(serializers.ModelSerializer):
    """Employee self-service profile.

    Employees may update only their own contact details; identity and
    organisational fields remain read-only (HR-controlled).
    """

    department_name = serializers.CharField(
        source='department.name',
        read_only=True
    )

    designation_title = serializers.CharField(
        source='designation.title',
        read_only=True
    )

    class Meta:
        model = Employee
        fields = [
            'id',
            'first_name',
            'last_name',
            'employee_code',
            'email',
            'phone',
            'address',
            'date_of_birth',
            'branch',
            'department_name',
            'designation_title',
            'status',
        ]
        read_only_fields = [
            'first_name',
            'last_name',
            'employee_code',
            'branch',
            'department_name',
            'designation_title',
            'status',
        ]
