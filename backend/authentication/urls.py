from django.urls import path

from .views import me, my_profile

urlpatterns = [
    path('me/', me),
    path('me/profile/', my_profile),
]
