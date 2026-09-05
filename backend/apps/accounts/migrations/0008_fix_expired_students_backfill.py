from datetime import timedelta

from django.db import migrations


def fix_incorrectly_expired_students(apps, schema_editor):
    from django.utils import timezone

    User = apps.get_model('accounts', 'User')
    now = timezone.now()
    User.objects.filter(
        role='student',
        access_expires_at__isnull=False,
        access_expires_at__lt=now,
    ).update(
        access_expires_at=now + timedelta(days=90),
        is_active_student=True,
        is_active=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_user_profile_choices'),
    ]

    operations = [
        migrations.RunPython(fix_incorrectly_expired_students, migrations.RunPython.noop),
    ]
