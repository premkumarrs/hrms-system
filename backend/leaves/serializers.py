from rest_framework import serializers

from . import services
from .models import Leave, Permission


class LeaveSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True,
    )

    approved_by_name = serializers.SerializerMethodField()

    leave_type_display = serializers.CharField(
        source='get_leave_type_display',
        read_only=True
    )

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    number_of_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = Leave

        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'leave_type',
            'leave_type_display',
            'start_date',
            'end_date',
            'number_of_days',
            'reason',
            'status',
            'status_display',
            'approved_by',
            'approved_by_name',
            'created_at',
            'updated_at',
        ]

        # Status / approver are managed via the approve & reject actions.
        read_only_fields = [
            'status',
            'approved_by',
            'created_at',
            'updated_at',
        ]

    def get_employee_name(self, obj):
        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
        return None

    def validate(self, attrs):
        start = attrs.get('start_date')
        end = attrs.get('end_date')

        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be before start date."}
            )

        employee = attrs.get('employee')
        if employee is None and self.instance:
            employee = self.instance.employee

        leave_type = attrs.get('leave_type')
        if leave_type is None and self.instance:
            leave_type = self.instance.leave_type

        if employee and leave_type and start and end:
            exclude_id = self.instance.pk if self.instance else None
            ok, message = services.validate_leave_balance(
                employee, leave_type, start, end, exclude_leave_id=exclude_id
            )
            if not ok:
                raise serializers.ValidationError({"leave_type": message})

        return attrs


class PermissionSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True,
    )

    approved_by_name = serializers.SerializerMethodField()

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = Permission

        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'date',
            'from_time',
            'to_time',
            'reason',
            'status',
            'status_display',
            'approved_by',
            'approved_by_name',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'status',
            'approved_by',
            'created_at',
            'updated_at',
        ]

    def get_employee_name(self, obj):
        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
        return None

    def validate(self, attrs):
        start = attrs.get('from_time')
        end = attrs.get('to_time')

        if start and end and end <= start:
            raise serializers.ValidationError(
                {"to_time": "End time must be after start time."}
            )

        return attrs
