# Срок доступа ученика теперь настраивается вручную (день/неделя/месяц —
# на выбор администратора) вместо жёстко зашитого периода.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_birth_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='access_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
