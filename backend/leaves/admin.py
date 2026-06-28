from django.contrib import admin
from .models import Leave, Permission


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'leave_type',
        'start_date',
        'end_date',
        'status',
        'approved_by',
    )

    list_filter = ('status', 'leave_type')

    search_fields = (
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    )

    date_hierarchy = 'start_date'

    ordering = ('-created_at',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'date',
        'from_time',
        'to_time',
        'status',
        'approved_by',
    )

    list_filter = ('status', 'date')

    search_fields = (
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    )

    date_hierarchy = 'date'

    ordering = ('-date',)
