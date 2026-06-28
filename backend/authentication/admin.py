from django.contrib import admin
from .models import UserProfile, AuditLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = ('user', 'role', 'employee')

    list_filter = ('role',)

    search_fields = ('user__username',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = (
        'created_at', 'action', 'username', 'target_model', 'target_id', 'ip_address',
    )
    list_filter = ('action', 'target_model')
    search_fields = ('username', 'target_repr', 'target_id')
    readonly_fields = (
        'user', 'username', 'action', 'target_model', 'target_id',
        'target_repr', 'changes', 'ip_address', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
