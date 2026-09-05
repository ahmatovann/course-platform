from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_user_access_expires_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar_emoji',
            field=models.CharField(blank=True, default='', max_length=8),
        ),
        migrations.AddField(
            model_name='user',
            name='background',
            field=models.ImageField(blank=True, null=True, upload_to='profile_backgrounds/'),
        ),
    ]
