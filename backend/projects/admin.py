from django.contrib import admin
from .models import Project, ProjectAllocation


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):

    list_display = ('name', 'client', 'start_date', 'end_date', 'status')

    list_filter = ('status',)

    search_fields = ('name', 'client')

    ordering = ('-start_date',)


@admin.register(ProjectAllocation)
class ProjectAllocationAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'project',
        'role',
        'allocated_on',
        'released_on',
    )

    list_filter = ('project',)

    search_fields = (
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
        'project__name',
    )

    ordering = ('-allocated_on',)
