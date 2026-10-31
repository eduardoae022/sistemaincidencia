from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.catalogos.models import Categoria, ServicioAfectado, SLA


class Ticket(models.Model):
    """
    Entidad central del sistema — instrumento de medición de la tesis.
    Cada campo cumple un rol específico en la recolección de datos.
    """

    # ── Estados del ciclo de vida ────────────────────────────────────────────
    ESTADO_REGISTRADO = 'Registrado'
    ESTADO_CLASIFICADO = 'Clasificado'
    ESTADO_ASIGNADO = 'Asignado'
    ESTADO_EN_ATENCION = 'En atención'
    ESTADO_EN_ESPERA = 'En espera'
    ESTADO_RESUELTO = 'Resuelto'
    ESTADO_CERRADO = 'Cerrado'
    ESTADO_REABIERTO = 'Reabierto'

    ESTADO_CHOICES = [
        (ESTADO_REGISTRADO, 'Registrado'),
        (ESTADO_CLASIFICADO, 'Clasificado'),
        (ESTADO_ASIGNADO, 'Asignado'),
        (ESTADO_EN_ATENCION, 'En atención'),
        (ESTADO_EN_ESPERA, 'En espera'),
        (ESTADO_RESUELTO, 'Resuelto'),
        (ESTADO_CERRADO, 'Cerrado'),
        (ESTADO_REABIERTO, 'Reabierto'),
    ]

    # ── Prioridades ──────────────────────────────────────────────────────────
    PRIORIDAD_ALTA = 'Alta'
    PRIORIDAD_MEDIA = 'Media'
    PRIORIDAD_BAJA = 'Baja'

    PRIORIDAD_CHOICES = [
        (PRIORIDAD_ALTA, 'Alta'),
        (PRIORIDAD_MEDIA, 'Media'),
        (PRIORIDAD_BAJA, 'Baja'),
    ]

    # ── Campos principales ───────────────────────────────────────────────────
    descripcion = models.TextField(
        verbose_name='Descripción de la incidencia',
        help_text='Describa detalladamente el problema, síntomas y contexto'
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name='Categoría',
        related_name='tickets'
    )
    servicio_afectado = models.ForeignKey(
        ServicioAfectado,
        on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name='Servicio afectado',
        related_name='tickets'
    )
    solicitante = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='tickets_solicitados',
        verbose_name='Solicitante'
    )

    # ── Prioridades (tres distintas por diseño de la tesis) ──────────────────
    prioridad_operador = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        null=True, blank=True,
        verbose_name='Prioridad (Operador)',
        help_text='Asignada manualmente por el operador — NUNCA se sobrescribe'
    )
    prioridad_correcta = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        null=True, blank=True,
        verbose_name='Prioridad correcta',
        help_text='Validada por el jefe de soporte — ground truth para el modelo ML'
    )
    prioridad_modelo = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        null=True, blank=True,
        verbose_name='Prioridad (Modelo ML)',
        help_text='Sugerencia del modelo Random Forest (Fase 3). Null si el servicio no respondió.'
    )
    confianza_modelo = models.FloatField(
        null=True, blank=True,
        verbose_name='Confianza del modelo',
        help_text='Probabilidad de la clase predicha (0-1). Null si el servicio no respondió.'
    )
    # Captura si el operador siguió la sugerencia en el momento de clasificar.
    # No puede reconstruirse retroactivamente — null para tickets sin sugerencia disponible.
    siguio_sugerencia_ia = models.BooleanField(
        null=True, blank=True,
        verbose_name='¿Siguió sugerencia IA?',
        help_text=(
            'True si prioridad_operador coincidió con prioridad_modelo al clasificar. '
            'Null si no hubo sugerencia disponible (servicio caído o ticket pre-despliegue).'
        )
    )

    # ── Estado y asignación ──────────────────────────────────────────────────
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_REGISTRADO,
        verbose_name='Estado'
    )
    tecnico_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tickets_asignados',
        verbose_name='Técnico asignado'
    )

    # ── Fechas y tiempos ─────────────────────────────────────────────────────
    fecha_hora_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha/hora de registro'
    )
    fecha_hora_primera_atencion = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Fecha/hora de primera atención',
        help_text='Se estampa SOLO al presionar "Tomar ticket" — nunca automáticamente'
    )
    fecha_hora_cierre = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Fecha/hora de cierre'
    )

    # ── SLA ──────────────────────────────────────────────────────────────────
    sla_maximo_horas = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='SLA máximo (horas)',
        help_text='Calculado desde tabla SLA al momento de clasificar'
    )
    dentro_sla = models.BooleanField(
        null=True, blank=True,
        verbose_name='¿Dentro del SLA?',
        help_text='Calculado al resolver comparando tiempo transcurrido vs SLA máximo'
    )

    # ── Resolución ───────────────────────────────────────────────────────────
    solucion_aplicada = models.TextField(
        null=True, blank=True,
        verbose_name='Solución aplicada',
        help_text='Obligatorio para poder resolver el ticket'
    )

    # ── Reapertura ───────────────────────────────────────────────────────────
    es_reapertura = models.BooleanField(
        default=False,
        verbose_name='¿Es reapertura?',
        help_text='True si este ticket es la reapertura de otro ticket anterior'
    )
    ticket_original = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reaperturas',
        verbose_name='Ticket original',
        help_text='Referencia al ticket original si este es una reapertura'
    )

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-fecha_hora_registro']

    def __str__(self):
        return self.codigo

    @property
    def codigo(self):
        """Formato visible: TK-0001"""
        return f'TK-{self.pk:04d}'

    def calcular_horas_transcurridas(self):
        """Horas transcurridas desde el registro hasta ahora (o hasta cierre)"""
        fin = self.fecha_hora_cierre or timezone.now()
        delta = fin - self.fecha_hora_registro
        return delta.total_seconds() / 3600

    def calcular_horas_hasta_primera_atencion(self):
        """TPA: Tiempo de Primera Atención en horas"""
        if not self.fecha_hora_primera_atencion:
            return None
        delta = self.fecha_hora_primera_atencion - self.fecha_hora_registro
        return round(delta.total_seconds() / 3600, 2)

    def calcular_sla_restante_horas(self):
        """Horas restantes de SLA (negativo si vencido)"""
        if not self.sla_maximo_horas:
            return None
        if self.estado in [self.ESTADO_CERRADO, self.ESTADO_RESUELTO]:
            return None
        horas_transcurridas = self.calcular_horas_transcurridas()
        return round(self.sla_maximo_horas - horas_transcurridas, 2)

    def estado_sla(self):
        """
        Retorna: 'ok', 'advertencia', 'vencido', o 'cerrado'
        Para mostrar el indicador de color en la bandeja.
        """
        if self.estado in [self.ESTADO_CERRADO, self.ESTADO_RESUELTO]:
            return 'cerrado'
        restante = self.calcular_sla_restante_horas()
        if restante is None:
            return 'sin_sla'
        if restante < 0:
            return 'vencido'
        if self.sla_maximo_horas and restante < (self.sla_maximo_horas * 0.20):
            return 'advertencia'
        return 'ok'

    def puede_tomar(self, usuario):
        """El técnico asignado puede tomar el ticket si está en estado 'Asignado'"""
        return (
            self.estado == self.ESTADO_ASIGNADO and
            self.tecnico_asignado == usuario and
            not self.fecha_hora_primera_atencion
        )

    def puede_resolver(self, usuario):
        return (
            self.estado in [self.ESTADO_EN_ATENCION, self.ESTADO_EN_ESPERA] and
            self.tecnico_asignado == usuario
        )

    def puede_reabrir(self, usuario):
        return self.estado in [self.ESTADO_RESUELTO, self.ESTADO_CERRADO]


class BitacoraTicket(models.Model):
    """
    Registro de auditoría — append-only, sin edición ni borrado.
    Toda transición de estado y acción relevante debe registrarse aquí.
    """
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='bitacora',
        verbose_name='Ticket'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Usuario'
    )
    accion = models.CharField(
        max_length=100,
        verbose_name='Acción',
        help_text='Ej: Cambio de estado, Reasignación, Comentario'
    )
    detalle = models.TextField(
        blank=True,
        verbose_name='Detalle'
    )
    valor_anterior = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Valor anterior'
    )
    valor_nuevo = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Valor nuevo'
    )
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha/hora'
    )

    class Meta:
        verbose_name = 'Bitácora de Ticket'
        verbose_name_plural = 'Bitácora de Tickets'
        ordering = ['fecha_hora']

    def __str__(self):
        return f'{self.ticket.codigo} | {self.accion} | {self.fecha_hora}'

    def delete(self, *args, **kwargs):
        """La bitácora es append-only: no se puede eliminar ningún registro"""
        raise ValidationError('Los registros de auditoría no pueden eliminarse.')

    def save(self, *args, **kwargs):
        """Solo se permite la creación inicial — no se puede editar"""
        if self.pk:
            raise ValidationError('Los registros de auditoría no pueden modificarse.')
        super().save(*args, **kwargs)


class Comentario(models.Model):
    """Hilo de comentarios entre solicitante y técnico"""
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comentarios',
        verbose_name='Ticket'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Usuario'
    )
    texto = models.TextField(verbose_name='Comentario')
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha/hora'
    )

    class Meta:
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['fecha_hora']

    def __str__(self):
        return f'{self.ticket.codigo} | {self.usuario.username} | {self.fecha_hora}'
