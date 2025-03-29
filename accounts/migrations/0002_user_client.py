# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),  
        ('accounts', '0001_initial'),  # Referência à migração anterior do app accounts
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='client',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users',
                to='clients.client',
                verbose_name='Cliente'
            ),
        ),
    ]
