import random
import string

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


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
