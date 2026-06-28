from django.db.models.signals import post_save
from django.dispatch import receiver

from .groups import sync_profile_groups
from .models import UserProfile


@receiver(post_save, sender=UserProfile)
def sync_groups_on_profile_save(sender, instance, **kwargs):
    sync_profile_groups(instance)
