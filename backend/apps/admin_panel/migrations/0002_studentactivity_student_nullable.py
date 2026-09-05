from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('admin_panel', '0001_studentactivity')]

    operations = [
        migrations.AlterField(
            model_name='studentactivity',
            name='student',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='activity_log', to='accounts.user'),
        ),
    ]