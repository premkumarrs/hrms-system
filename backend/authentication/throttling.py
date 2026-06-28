"""Rate limits for authentication endpoints."""

from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'


class TokenRefreshRateThrottle(AnonRateThrottle):
    scope = 'token_refresh'
