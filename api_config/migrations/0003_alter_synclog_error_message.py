# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_config', '0002_add_task_id_to_synclog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='synclog',
            name='error_message',
            field=models.TextField(blank=True, null=True, verbose_name='Mensagem de Erro'),
        ),
    ]
