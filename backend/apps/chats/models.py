from django.conf import settings
from django.db import models


class ChatThread(models.Model):
    """Чат бывает двух видов: групповой (все ученики курса + админ) и
    личный (конкретный ученик ↔ преподаватель/админ)."""

    class Kind(models.TextChoices):
        GROUP = 'group', 'Групповой чат курса'
        DIRECT = 'direct', 'Чат с преподавателем'

    kind = models.CharField(max_length=10, choices=Kind.choices)
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, null=True, blank=True, related_name='chat_threads'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='direct_threads'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['course'], condition=models.Q(kind='group'), name='unique_group_thread_per_course',
            ),
            models.UniqueConstraint(
                fields=['student'], condition=models.Q(kind='direct'), name='unique_direct_thread_per_student',
            ),
        ]

    @property
    def title(self):
        if self.kind == self.Kind.GROUP:
            return f'{self.course.title} — общий чат' if self.course_id else 'Общий чат'
        return 'Чат с преподавателем'

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    # Текст необязателен, если это голосовое сообщение (есть audio_file) —
    # ровно одно из двух (text или audio_file) должно быть заполнено,
    # проверяется в ChatMessageListView.post().
    text = models.TextField(blank=True, default='')
    audio_file = models.FileField(upload_to='chats/audio/', blank=True, null=True)
    # Произвольное вложение (фото/документ/архив и т.д.), отдельно от голосового.
    file = models.FileField(upload_to='chats/files/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, default='')
    # «Удалить у всех» — сообщение считается удалённым для всех участников.
    deleted_for_everyone = models.BooleanField(default=False)
    # «Удалить у меня» — сообщение скрыто только для перечисленных пользователей.
    deleted_for = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='hidden_chat_messages',
    )
    favorited_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='favorite_chat_messages',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender}: {self.text[:40] or "[голосовое сообщение]"}'
