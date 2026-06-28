from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from authentication.token_views import AuditedTokenObtainPairView
from authentication.token_refresh import ThrottledTokenRefreshView
from config.health import health, health_ready

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/health/', health),
    path('api/health/ready/', health_ready),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/', include('employees.urls')),
    path('api/', include('attendance.urls')),
    path('api/', include('leaves.urls')),
    path('api/', include('projects.urls')),
    path('api/', include('dashboard.urls')),
    path('api/', include('documents.urls')),
    path('api/', include('lifecycle.urls')),
    path('api/', include('authentication.urls')),
    path('api/', include('notifications.urls')),
    path('api/', include('payroll.urls')),

    path('api/token/', AuditedTokenObtainPairView.as_view()),
    path('api/token/refresh/', ThrottledTokenRefreshView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )