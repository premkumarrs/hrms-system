from django.db.models import Q

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from .scheduler import run_scheduled_notifications


class NotificationViewSet(viewsets.ModelViewSet):
    """Notifications visible to the current user (personal + broadcast)."""

    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = (
            Notification.objects
            .select_related('employee')
            .filter(Q(recipient=user) | Q(recipient__isnull=True))
            .order_by('-created_at')
        )

        unread = self.request.query_params.get('unread')
        if unread is not None and unread.lower() in ('1', 'true', 'yes'):
            qs = qs.filter(is_read=False)

        return qs

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        user = request.user
        count = Notification.objects.filter(
            Q(recipient=user) | Q(recipient__isnull=True),
            is_read=False,
        ).count()
        return Response({"unread": count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"updated": updated})

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate today's birthday / anniversary / pending-approval alerts."""
        created = run_scheduled_notifications()
        return Response(
            {"created": created},
            status=status.HTTP_201_CREATED
        )
