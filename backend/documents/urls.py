from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentCategoryViewSet,
    EmployeeDocumentViewSet
)

router = DefaultRouter()

router.register(r'document-categories', DocumentCategoryViewSet)
router.register(r'documents', EmployeeDocumentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
