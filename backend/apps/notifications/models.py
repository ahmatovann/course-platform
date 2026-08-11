from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Внутриплатформенное уведомление. Показывается колокольчиком в шапке."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    text = models.CharField(max_length=300)
    url = models.CharField(max_length=300, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user_id}: {self.text[:40]}'


def notify(user, text, url=''):
    """Создать уведомление для одного пользователя."""
    return Notification.objects.create(user=user, text=text, url=url)


def notify_many(users, text, url=''):
    """Создать одно и то же уведомление сразу для нескольких пользователей."""
    Notification.objects.bulk_create([
        Notification(user=u, text=text, url=url) for u in users
    ])
