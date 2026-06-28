from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProjectViewSet,
    ProjectAllocationViewSet
)

router = DefaultRouter()

router.register(r'projects', ProjectViewSet)
router.register(r'allocations', ProjectAllocationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]