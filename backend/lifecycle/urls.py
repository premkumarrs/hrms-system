from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OnboardingViewSet, ResignationViewSet

router = DefaultRouter()

router.register(r'onboardings', OnboardingViewSet)
router.register(r'resignations', ResignationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
