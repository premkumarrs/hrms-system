from rest_framework import serializers

from .models import (
    Department,
    Designation,
    Employee,
    Education,
    BankDetails,
    IDProof,
    EmergencyContact
)


class DepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = '__all__'

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Department name is required.")

        qs = Department.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A department with this name already exists."
            )
        return value


class DesignationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Designation
        fields = '__all__'

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Designation title is required.")

        qs = Designation.objects.filter(title__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A designation with this title already exists."
            )
        return value


class EmployeeSerializer(serializers.ModelSerializer):

    department_name = serializers.CharField(
        source='department.name',
        read_only=True
    )

    designation_title = serializers.CharField(
        source='designation.title',
        read_only=True
    )

    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = '__all__'

    def get_manager_name(self, obj):

        if obj.manager:
            return f"{obj.manager.first_name} {obj.manager.last_name}"

        return None


class EducationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Education
        fields = [
            'id',
            'employee',
            'degree',
            'institution',
            'university',
            'year_of_passing',
            'percentage',
        ]


class BankDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankDetails
        fields = [
            'id',
            'employee',
            'bank_name',
            'branch',
            'account_number',
            'ifsc_code',
            'pan_number',
            'aadhaar_number',
        ]


class IDProofSerializer(serializers.ModelSerializer):

    class Meta:
        model = IDProof
        fields = [
            'id',
            'employee',
            'aadhaar_number',
            'pan_number',
            'passport_number',
            'driving_license',
        ]


class EmergencyContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmergencyContact
        fields = [
            'id',
            'employee',
            'contact_name',
            'relationship',
            'phone',
            'address',
        ]