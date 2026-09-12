import random
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


# Доступ ученика действует 3 месяца с момента создания/продления — по
# истечении этого срока учётная запись автоматически переводится в статус
# «Не активен» (см. deactivate_expired_students). ~3 месяца = 90 дней —
# в проекте нет отдельного планировщика задач (Celery/cron), поэтому
# проверка запускается «лениво»: при каждом открытии списка учеников в
# админке (StudentListView) и при каждой попытке входа ученика (LoginView).
ACCESS_PERIOD = timedelta(days=90)

# За сколько дней до истечения доступа отправлять ученику напоминание.
ACCESS_REMINDER_DAYS_BEFORE = 3


def deactivate_expired_students():
    """Переводит в статус «Не активен» всех учеников, у которых истёк срок
    доступа (access_expires_at в прошлом), и которые всё ещё числятся
    активными. Ничего не делает с учениками без установленного срока
    (access_expires_at is None) — им доступ не ограничен."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    User.objects.filter(
        role=User.Role.STUDENT, is_active_student=True,
        access_expires_at__isnull=False, access_expires_at__lt=timezone.now(),
    ).update(is_active_student=False, is_active=False)


def send_access_expiry_reminders():
    """Отправляет ученикам, у которых доступ истекает в ближайшие
    ACCESS_REMINDER_DAYS_BEFORE дней, личное сообщение в чат с
    преподавателем (плюс обычное уведомление-колокольчик). Как и
    deactivate_expired_students, запускается «лениво» — при каждом открытии
    списка учеников в админке и при каждом входе ученика, — отдельного
    планировщика задач (Celery/cron) в проекте нет.

    Каждому ученику напоминание уходит один раз на конкретный срок доступа
    (см. User.access_reminder_sent_for) — если админ продлит доступ, срок
    изменится и напоминание для нового срока отправится заново."""
    from django.contrib.auth import get_user_model
    from apps.chats.services import ensure_direct_thread
    from apps.chats.models import ChatMessage
    from apps.notifications.models import notify

    User = get_user_model()

    admin_user = User.objects.filter(role=User.Role.ADMIN).order_by('id').first()
    if not admin_user:
        return

    now = timezone.now()
    window_end = now + timedelta(days=ACCESS_REMINDER_DAYS_BEFORE)
    students = User.objects.filter(
        role=User.Role.STUDENT, is_active_student=True,
        access_expires_at__isnull=False,
        access_expires_at__gt=now, access_expires_at__lte=window_end,
    ).exclude(access_reminder_sent_for=F('access_expires_at'))

    for student in students:
        thread = ensure_direct_thread(student)
        text = (
            f'Здравствуйте, {student.first_name or student.get_full_name() or "ученик"}! '
            f'Напоминаем, что ваш доступ к обучению истекает '
            f'{timezone.localtime(student.access_expires_at):%d.%m.%Y}. '
            f'Если нужно продлить — напишите нам здесь или свяжитесь с администратором.'
        )
        ChatMessage.objects.create(thread=thread, sender=admin_user, text=text)
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
