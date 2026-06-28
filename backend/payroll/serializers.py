from rest_framework import serializers

from .models import SalaryRecord


class SalaryRecordSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()

    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True
    )

    net_salary = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = SalaryRecord
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'period',
            'basic_salary',
            'allowances',
            'deductions',
            'net_salary',
            'remarks',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def get_employee_name(self, obj):
        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return None
