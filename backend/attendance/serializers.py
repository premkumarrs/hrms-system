from rest_framework import serializers
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()

    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True
    )

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = Attendance

        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'date',
            'check_in',
            'check_out',
            'working_hours',
            'late_entry',
            'status',
            'status_display',
            'remarks',
            'created_at',
        ]

        # Derived server-side from check_in / check_out.
        read_only_fields = ['working_hours', 'late_entry', 'created_at']

    def get_employee_name(self, obj):

        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()

        return None
