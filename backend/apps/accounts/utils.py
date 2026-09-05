import random
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

# Сколько календарных дней в одной единице периода доступа — администратор
# выбирает единицу (день/неделя/месяц) и количество, а не только фиксированные
# «3 месяца» как раньше.
ACCESS_UNIT_DAYS = {'day': 1, 'week': 7, 'month': 30}
DEFAULT_ACCESS_AMOUNT = 3
DEFAULT_ACCESS_UNIT = 'month'


def period_to_timedelta(amount, unit):
    """Переводит выбранные администратором количество+единицу (например,
    «5 дней» или «2 недели») в timedelta. При некорректных значениях
    подстраховывается разумным значением по умолчанию (3 месяца)."""
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        amount = DEFAULT_ACCESS_AMOUNT
    amount = max(1, min(amount, 3650))
    days_per_unit = ACCESS_UNIT_DAYS.get(unit, ACCESS_UNIT_DAYS[DEFAULT_ACCESS_UNIT])
    return timedelta(days=amount * days_per_unit)


def deactivate_expired_students():
    """Переводит в статус «Не активен» учеников, у которых истёк срок
    доступа (access_expires_at в прошлом). Вызывается перед показом списка
    учеников в админке, отдельного фонового планировщика в проекте нет."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    now = timezone.now()
    User.objects.filter(
        role=User.Role.STUDENT, is_active_student=True,
        access_expires_at__isnull=False, access_expires_at__lte=now,
    ).update(is_active_student=False, is_active=False)


def send_access_expiry_reminders():
    from django.contrib.auth import get_user_model
    from django.db.models import F
    from apps.chats.models import ChatMessage
    from apps.chats.services import ensure_direct_thread
    from apps.notifications.models import notify

    User = get_user_model()
    admin_user = User.objects.filter(role=User.Role.ADMIN).order_by('id').first()
    if not admin_user:
        return

    now = timezone.now()
    window_end = now + timedelta(days=3)
    students = User.objects.filter(
        role=User.Role.STUDENT,
        is_active_student=True,
        access_expires_at__isnull=False,
        access_expires_at__gt=now,
        access_expires_at__lte=window_end,
    ).exclude(access_reminder_sent_for=F('access_expires_at'))

    for student in students:
        thread = ensure_direct_thread(student)
        ChatMessage.objects.create(
            thread=thread,
            sender=admin_user,
            text=(
                f'Здравствуйте, {student.first_name or student.get_full_name() or "ученик"}! '
                f'Ваш доступ к обучению истекает '
                f'{timezone.localtime(student.access_expires_at):%d.%m.%Y}. '
                'Если нужно продлить доступ, напишите администратору.'
            ),
        )
        notify(student, 'Скоро истекает доступ к обучению', url='/chats')
        student.access_reminder_sent_for = student.access_expires_at
        student.save(update_fields=['access_reminder_sent_for'])


def generate_password(length=10):
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    return ''.join(random.choices(chars, k=length))


def send_welcome_email(user, password):
    subject = 'Доступ к платформе COURSE'
    message = (
        f'Здравствуйте, {user.get_full_name() or user.username}!\n\n'
        f'Ваш аккаунт создан.\n'
        f'Логин: {user.email}\n'
        f'Временный пароль: {password}\n\n'
        f'Войдите на платформе и смените пароль в профиле.'
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
    subject = 'Восстановление пароля — COURSE'
    message = (
        f'Здравствуйте, {user.get_full_name() or user.username}!\n\n'
        f'Вы (или кто-то другой) запросили сброс пароля для аккаунта {user.email}.\n'
        f'Перейдите по ссылке, чтобы задать новый пароль:\n{link}\n\n'
        f'Ссылка действует один раз. Если вы не запрашивали сброс пароля — просто'
        f' проигнорируйте это письмо, пароль останется прежним.'
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
