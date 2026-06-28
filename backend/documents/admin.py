from django.contrib import admin
from .models import DocumentCategory, EmployeeDocument


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):

    list_display = ('employee', 'title', 'category', 'uploaded_at')

    list_filter = ('category',)

    search_fields = (
        'title',
        'employee__first_name',
        'employee__last_name',
        'employee__employee_code',
    )

    ordering = ('-uploaded_at',)
