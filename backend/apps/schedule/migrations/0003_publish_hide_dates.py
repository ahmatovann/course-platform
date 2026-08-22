# Дата рассылки (обязательная) вместо старого "дата и время события" +
# необязательная дата скрытия — новости теперь публикуются/скрываются по
# дате, без отдельного поля времени (время, если важно, пишется текстом в
# описании).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedule", "0002_scheduleevent_link_url"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scheduleevent",
            old_name="starts_at",
            new_name="publish_at",
        ),
        migrations.AlterField(
            model_name="scheduleevent",
            name="publish_at",
            field=models.DateField(
                help_text="Дата рассылки — с этой даты новость видна ученикам",
            ),
        ),
        migrations.AddField(
            model_name="scheduleevent",
            name="hide_at",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Необязательно — после этой даты новость скрывается от учеников",
            ),
        ),
        migrations.AlterModelOptions(
            name="scheduleevent",
            options={"ordering": ["-publish_at", "-id"]},
        ),
    ]
