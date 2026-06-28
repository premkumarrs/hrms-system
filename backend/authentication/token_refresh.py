"""JWT refresh with rate limiting."""

from rest_framework_simplejwt.views import TokenRefreshView

from .throttling import TokenRefreshRateThrottle


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [TokenRefreshRateThrottle]
