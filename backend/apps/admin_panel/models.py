from django.conf import settings
from django.db import models


class AuditLogEntry(models.Model):
    """Журнал действий администратора — раздел «История» в Настройках.
    Не строгий аудит безопасности (не хранит «было/стало»), а простой
    список «кто/что/когда» для быстрого разбора: кто создал ученика,
    кто удалил урок и т.д."""
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+',
    )
    action = models.CharField(max_length=20)  # created / updated / deleted / toggled
    target_type = models.CharField(max_length=40)  # «ученик», «тренинг», «урок» и т.д.
    target_repr = models.CharField(max_length=255)  # человекочитаемое название объекта
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.actor} {self.action} {self.target_type} «{self.target_repr}»'


def log_action(request, action, target_type, target_repr):
    """Записать одно действие в историю. Тихо игнорирует ошибки (история —
    вспомогательная функция, не должна ронять основной запрос)."""
    try:
        AuditLogEntry.objects.create(
            actor=getattr(request, 'user', None) if getattr(request.user, 'is_authenticated', False) else None,
            action=action, target_type=target_type, target_repr=target_repr[:255],
        )
    except Exception:
        pass
