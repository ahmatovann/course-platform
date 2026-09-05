# Пустая миграция-заглушка — оставлена под тем же именем/номером на месте
# более ранней (уже отменённой) попытки сделать Material.lessons
# ManyToMany. Ничего не меняет в базе: модель Material снова использует
# обычное поле lesson (ForeignKey, см. 0006_material_lesson_nullable.py).
# Если этот файл когда-либо будет применён через `migrate`, он безопасен —
# просто ничего не делает.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_material_lesson_nullable'),
    ]

    operations = []
