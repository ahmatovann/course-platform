from django.conf import settings
from django.db import models


class ScheduleEvent(models.Model):
    """Новость. Если course не указан — новость общая и видна всем
    ученикам, иначе только тем, кто записан на этот курс.

    Время не хранится отдельным полем — если оно важно, администратор
    просто указывает его текстом внутри описания; обе даты ниже — это
    только даты (без времени)."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    link_url = models.URLField(blank=True, default='', help_text='Необязательная ссылка на подробности/внешний ресурс')
    # Дата рассылки — новость становится видна ученикам начиная с этой
    # даты (до неё видна только администратору как запланированная).
    publish_at = models.DateField(help_text='Дата рассылки — с этой даты новость видна ученикам')
    # Необязательная дата, после которой новость автоматически скрывается
    # (архивируется) от учеников — сама запись при этом не удаляется,
    # админ по-прежнему её видит и может отредактировать/вернуть.
    hide_at = models.DateField(
        null=True, blank=True,
        help_text='Необязательно — после этой даты новость скрывается от учеников',
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_events'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-publish_at', '-id']

    def __str__(self):
        return f'{self.publish_at:%d.%m.%Y} — {self.title}'
