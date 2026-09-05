from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Администратор'
        STUDENT = 'student', 'Ученик'

    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    avatar_emoji = models.CharField(max_length=8, blank=True, default='')
    background = models.ImageField(upload_to='profile_backgrounds/', blank=True, null=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=32, blank=True, default='')
    phone_verified = models.BooleanField(default=False)
    birth_date = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=64, blank=True, default='')
    city = models.CharField(max_length=64, blank=True, default='')
    is_active_student = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=True)
    # Срок доступа ученика к платформе — администратор сам задаёт период
    # (в днях/неделях/месяцах) при создании ученика и может продлевать его
    # позже на любой выбранный период. Когда срок истекает, ученик
    # автоматически переводится в статус «Не активен» (см.
    # apps.accounts.utils.deactivate_expired_students).
    access_expires_at = models.DateTimeField(blank=True, null=True)
    access_reminder_sent_for = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f'{self.get_full_name() or self.username} <{self.email}>'
