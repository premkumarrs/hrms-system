from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UserProfile
from .permissions import get_role, get_permissions, get_profile
from .serializers import SelfProfileSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return the current user's identity, role and permission flags."""

    user = request.user
    role = get_role(user)

    profile = get_profile(user)
    employee = profile.employee if profile else None

    employee_data = None
    if employee:
        employee_data = {
            "id": employee.id,
            "name": f"{employee.first_name} {employee.last_name}".strip(),
            "employee_code": employee.employee_code,
        }

    return Response({
        "username": user.username,
        "role": role,
        "is_superuser": user.is_superuser,
        "employee": employee_data,
        "permissions": get_permissions(role),
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def my_profile(request):
    """Self-service: view or update the linked employee's own details."""

    profile = (
        UserProfile.objects
        .select_related('employee__department', 'employee__designation')
        .filter(user=request.user)
        .first()
    )
    employee = profile.employee if profile else None

    if employee is None:
        return Response(
            {"detail": "No employee profile is linked to your account."},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        return Response(SelfProfileSerializer(employee).data)

    serializer = SelfProfileSerializer(
        employee,
        data=request.data,
        partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)
