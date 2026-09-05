from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_material_lessons_m2m'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='require_lessons_watched',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='test',
            name='max_attempts',
            field=models.PositiveIntegerField(default=0, help_text='0 означает без ограничений'),
        ),
    ]