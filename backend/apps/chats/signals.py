from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.courses.models import Enrollment

from .services import ensure_group_thread


@receiver(post_save, sender=Enrollment)
def create_group_thread_on_enroll(sender, instance, created, **kwargs):
    """Как только ученика записали на курс — у курса точно есть групповой чат."""
    if created:
        ensure_group_thread(instance.course)
