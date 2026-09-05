# Материал теперь можно загрузить в раздел «Материалы» без привязки к
# уроку (lesson может быть NULL) — прикрепляется к уроку(-ам) позже.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_comment_video_timestamp_seconds'),
    ]

    operations = [
        migrations.AlterField(
            model_name='material',
            name='lesson',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='materials', to='courses.lesson',
            ),
        ),
    ]
