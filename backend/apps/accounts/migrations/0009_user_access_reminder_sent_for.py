from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_fix_expired_students_backfill'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='access_reminder_sent_for',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
