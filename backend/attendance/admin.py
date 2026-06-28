from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'date',
        'check_in',
        'check_out',
        'working_hours',
        'late_entry',
        'status',
    )

    list_filter = ('status', 'late_entry', 'date')

    search_fields = (
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    )

    date_hierarchy = 'date'

    ordering = ('-date',)
