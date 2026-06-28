from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentViewSet,
    DesignationViewSet,
    EmployeeViewSet,
    EducationViewSet,
    BankDetailsViewSet,
    IDProofViewSet,
    EmergencyContactViewSet
)

router = DefaultRouter()

router.register(r'departments', DepartmentViewSet)
router.register(r'designations', DesignationViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'education', EducationViewSet)
router.register(r'bank-details', BankDetailsViewSet)
router.register(r'id-proofs', IDProofViewSet)
router.register(r'emergency-contacts', EmergencyContactViewSet)

urlpatterns = [
    path('', include(router.urls)),
]