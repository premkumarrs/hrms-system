from django.contrib import admin

from .models import (
    Department,
    Designation,
    Employee,
    Education,
    BankDetails,
    IDProof,
    EmergencyContact
)


admin.site.register(Department)
admin.site.register(Designation)
admin.site.register(Employee)

admin.site.register(Education)
admin.site.register(BankDetails)
admin.site.register(IDProof)
admin.site.register(EmergencyContact)