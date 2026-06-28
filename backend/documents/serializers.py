import os

from rest_framework import serializers

from .models import DocumentCategory, EmployeeDocument
from .validators import safe_upload_filename, validate_upload_file


class DocumentCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = DocumentCategory
        fields = ['id', 'name']


class EmployeeDocumentSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()

    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True
    )

    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    file_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'category',
            'category_name',
            'title',
            'file',
            'file_name',
            'uploaded_at',
        ]
        read_only_fields = ['uploaded_at']

    def get_employee_name(self, obj):
        if obj.employee:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return None

    def get_file_name(self, obj):
        if obj.file:
            return os.path.basename(obj.file.name)
        return None

    def validate_file(self, value):
        if value is None:
            return value
        try:
            validate_upload_file(value)
        except Exception as exc:
            from django.core.exceptions import ValidationError as DjangoValidationError
            if isinstance(exc, DjangoValidationError):
                raise serializers.ValidationError(exc.messages)
            raise
        value.name = safe_upload_filename(value.name)
        return value
