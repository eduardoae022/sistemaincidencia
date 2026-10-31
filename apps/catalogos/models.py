from django.db import models


class Categoria(models.Model):
    """Categoría de incidencia: Red, Base de Datos, Aplicación, Hardware, Seguridad"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    activo = models.BooleanField(default=True, verbose_name='Activo',
                                 help_text='Desactivar en lugar de borrar para preservar la integridad histórica')

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ServicioAfectado(models.Model):
    """Servicio afectado que pertenece a una categoría"""
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='servicios',
        verbose_name='Categoría'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Servicio Afectado'
        verbose_name_plural = 'Servicios Afectados'
        ordering = ['categoria__nombre', 'nombre']
        unique_together = [['nombre', 'categoria']]

    def __str__(self):
        return f'{self.nombre} ({self.categoria})'


class SLA(models.Model):
    """Tiempo máximo de atención por nivel de prioridad — editable, nunca hardcodeado"""
    PRIORIDAD_CHOICES = [
        ('Alta', 'Alta'),
        ('Media', 'Media'),
        ('Baja', 'Baja'),
    ]
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        unique=True,
        verbose_name='Prioridad'
    )
    horas_maximas = models.PositiveIntegerField(
        verbose_name='Horas máximas',
        help_text='Tiempo máximo de resolución en horas para esta prioridad'
    )

    class Meta:
        verbose_name = 'SLA'
        verbose_name_plural = 'SLAs'
        ordering = ['prioridad']

    def __str__(self):
        return f'SLA {self.prioridad}: {self.horas_maximas}h'
