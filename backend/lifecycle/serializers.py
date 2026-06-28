from rest_framework import serializers

from .models import Onboarding, Resignation


class OnboardingSerializer(serializers.ModelSerializer):

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
        model = Onboarding
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'joining_date',
            'department_assigned',
            'designation_assigned',
            'documents_submitted',
            'status',
            'status_display',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_employee_name(self, obj):
        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return None


class ResignationSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()

    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True
    )

    exit_status_display = serializers.CharField(
        source='get_exit_status_display',
        read_only=True
    )

    final_settlement_status_display = serializers.CharField(
        source='get_final_settlement_status_display',
        read_only=True
    )

    expected_last_working_day = serializers.DateField(read_only=True)

    class Meta:
        model = Resignation
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'resignation_date',
            'notice_period_days',
            'last_working_day',
            'expected_last_working_day',
            'reason',
            'exit_status',
            'exit_status_display',
            'final_settlement_status',
            'final_settlement_status_display',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_employee_name(self, obj):
        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return None
