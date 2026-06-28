from django.contrib import admin
from .models import Onboarding, Resignation


@admin.register(Onboarding)
class OnboardingAdmin(admin.ModelAdmin):

    list_display = ('employee', 'joining_date', 'status')

    list_filter = ('status',)

    search_fields = (
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    )


@admin.register(Resignation)
class ResignationAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'resignation_date',
        'last_working_day',
        'exit_status',
        'final_settlement_status',
    )

    list_filter = ('exit_status', 'final_settlement_status')

    search_fields = (
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    )

    ordering = ('-resignation_date',)
