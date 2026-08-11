from django.conf import settings
from django.db import models


class ScheduleEvent(models.Model):
    """Событие в расписании: занятие, дедлайн теста и т.д. Если course не
    указан — событие общее и видно всем ученикам, иначе только тем, кто
    записан на этот курс."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    link_url = models.URLField(blank=True, default='', help_text='Необязательная ссылка на подробности/внешний ресурс')
    starts_at = models.DateTimeField()
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_events'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['starts_at']

    def __str__(self):
        return f'{self.starts_at:%d.%m.%Y %H:%M} — {self.title}'
