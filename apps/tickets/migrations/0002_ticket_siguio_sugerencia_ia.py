from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='siguio_sugerencia_ia',
            field=models.BooleanField(
                null=True,
                blank=True,
                verbose_name='¿Siguió sugerencia IA?',
                help_text=(
                    '[FASE 3] True si prioridad_operador coincidió con prioridad_modelo '
                    'al momento de clasificar. Null si no hubo sugerencia disponible '
                    '(servicio caído o ticket pre-despliegue). '
                    'No puede reconstruirse retroactivamente — se captura solo en el momento.'
                ),
            ),
        ),
    ]
