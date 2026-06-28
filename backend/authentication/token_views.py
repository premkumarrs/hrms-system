"""JWT login with audit logging."""

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .audit import log_audit
from .throttling import LoginRateThrottle


class AuditedTokenObtainPairView(TokenObtainPairView):
    """Issue JWT tokens and record login events."""

    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '')

        try:
            response = super().post(request, *args, **kwargs)
        except (AuthenticationFailed, ValidationError):
            log_audit(
                request,
                'login_failed',
                target_model='auth.user',
                target_repr=username,
                username=username,
            )
            raise

        if response.status_code == status.HTTP_200_OK:
            log_audit(
                request,
                'login_success',
                target_model='auth.user',
                target_repr=username,
                username=username,
            )
        else:
            log_audit(
                request,
                'login_failed',
                target_model='auth.user',
                target_repr=username,
                username=username,
            )

        return response
