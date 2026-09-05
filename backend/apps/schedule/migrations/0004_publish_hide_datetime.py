# Дата рассылки/скрытия новости теперь хранит ещё и время (не только дату) —
# администратор указывает точный момент объявления и скрытия.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedule", "0003_publish_hide_dates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scheduleevent",
            name="publish_at",
            field=models.DateTimeField(
                help_text="Дата и время рассылки — с этого момента новость видна ученикам",
            ),
        ),
        migrations.AlterField(
            model_name="scheduleevent",
            name="hide_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Необязательно — после этого момента новость скрывается от учеников",
            ),
        ),
        # У уже существующих записей поля хранили только дату (например,
        # "2026-08-01") — дополняем их временем 00:00, чтобы они остались
        # корректными значениями datetime и не ломались при чтении.
        migrations.RunSQL(
            sql="UPDATE schedule_scheduleevent SET publish_at = publish_at || ' 00:00:00' "
                "WHERE publish_at IS NOT NULL AND length(publish_at) = 10;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="UPDATE schedule_scheduleevent SET hide_at = hide_at || ' 00:00:00' "
                "WHERE hide_at IS NOT NULL AND length(hide_at) = 10;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
