from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Администратор'
        STUDENT = 'student', 'Ученик'

    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=32, blank=True, default='')
    phone_verified = models.BooleanField(default=False)
    birth_date = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=64, blank=True, default='')
    city = models.CharField(max_length=64, blank=True, default='')
    is_active_student = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=True)
    # Срок действия доступа ученика (создаётся/продлевается администратором
    # на 3 месяца вперёд — см. apps.accounts.utils.ACCESS_PERIOD). После
    # истечения срока deactivate_expired_students() автоматически снимает
    # is_active_student. Для администраторов и учеников без ограничения
    # доступа остаётся пустым (null) — тогда доступ бессрочный.
    access_expires_at = models.DateTimeField(null=True, blank=True)
    # Срок действия, для которого уже отправлено напоминание в личный чат с
    # преподавателем (см. accounts.utils.send_access_expiry_reminders).
    # Хранится именно значение access_expires_at, а не просто флаг — так при
    # продлении доступа (access_expires_at меняется) напоминание для нового
    # срока отправится заново, а повторно на один и тот же срок — нет.
    access_reminder_sent_for = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f'{self.get_full_name() or self.username} <{self.email}>'
