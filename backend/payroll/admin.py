from django.contrib import admin

from .models import SalaryRecord


@admin.register(SalaryRecord)
class SalaryRecordAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'period',
        'basic_salary',
        'allowances',
        'deductions',
    )

    list_filter = ('period',)

    search_fields = (
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    )

    ordering = ('-period',)
