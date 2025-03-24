# Generated manually

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('api_config', '0001_initial'),  # Certifique-se de que esta é a sua migração anterior
    ]

    operations = [
        migrations.AddField(
            model_name='synclog',
            name='task_id',
            field=models.CharField(blank=True, max_length=36, null=True, verbose_name='ID da Tarefa'),
        ),
    ]