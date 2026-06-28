from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):

    type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )

    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'employee',
            'employee_name',
            'notification_type',
            'type_display',
            'title',
            'message',
            'event_date',
            'is_read',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def get_employee_name(self, obj):
        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return None
