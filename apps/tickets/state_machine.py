"""
Máquina de estados centralizada para el ciclo de vida del Ticket.
TODA transición de estado debe pasar por aquí.
Cada transición válida escribe automáticamente en BitacoraTicket.
"""
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from apps.catalogos.models import SLA
from .models import Ticket, BitacoraTicket
from .prediccion_client import obtener_sugerencia



# ── Mapa de transiciones válidas ─────────────────────────────────────────────
TRANSICIONES_VALIDAS = {
    Ticket.ESTADO_REGISTRADO: [Ticket.ESTADO_CLASIFICADO],
    Ticket.ESTADO_CLASIFICADO: [Ticket.ESTADO_ASIGNADO],
    Ticket.ESTADO_ASIGNADO: [Ticket.ESTADO_EN_ATENCION],
    Ticket.ESTADO_EN_ATENCION: [Ticket.ESTADO_EN_ESPERA, Ticket.ESTADO_RESUELTO],
    Ticket.ESTADO_EN_ESPERA: [Ticket.ESTADO_EN_ATENCION, Ticket.ESTADO_RESUELTO],
    Ticket.ESTADO_RESUELTO: [Ticket.ESTADO_CERRADO],
    Ticket.ESTADO_CERRADO: [],
    Ticket.ESTADO_REABIERTO: [],
}


class TicketStateMachine:
    """
    Encapsula toda la lógica de transiciones de estado.
    Uso: TicketStateMachine(ticket, usuario).transicion(nuevo_estado, **kwargs)
    """

    def __init__(self, ticket, usuario):
        self.ticket = ticket
        self.usuario = usuario

    def _validar_transicion(self, nuevo_estado):
        """Verifica que la transición sea válida desde el estado actual"""
        estados_validos = TRANSICIONES_VALIDAS.get(self.ticket.estado, [])
        if nuevo_estado not in estados_validos:
            raise ValidationError(
                f'Transición no permitida: {self.ticket.estado} → {nuevo_estado}'
            )

    def _registrar_bitacora(self, accion, detalle='', valor_anterior='', valor_nuevo=''):
        """Crea un registro de auditoría"""
        BitacoraTicket.objects.create(
            ticket=self.ticket,
            usuario=self.usuario,
            accion=accion,
            detalle=detalle,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
        )

    def clasificar(self, categoria, servicio_afectado, prioridad_operador):
        """
        Registrado → Clasificado
        Asigna categoría, servicio y prioridad.
        Calcula sla_maximo_horas desde la tabla SLA.
        Solicita sugerencia al servicio de predicción — si falla, el flujo continúa sin sugerencia.
        """
        self._validar_transicion(Ticket.ESTADO_CLASIFICADO)

        # Calcular SLA desde la tabla — NUNCA hardcodeado
        try:
            sla = SLA.objects.get(prioridad=prioridad_operador)
            sla_horas = sla.horas_maximas
        except SLA.DoesNotExist:
            sla_horas = None

        estado_anterior = self.ticket.estado

        self.ticket.categoria = categoria
        self.ticket.servicio_afectado = servicio_afectado
        self.ticket.prioridad_operador = prioridad_operador
        self.ticket.sla_maximo_horas = sla_horas
        self.ticket.estado = Ticket.ESTADO_CLASIFICADO

        # Solicitar sugerencia al servicio de predicción.
        # Si el servicio no responde, el resultado es None y los campos quedan null —
        # el ticket se clasifica igual, el operador no queda bloqueado.
        sugerencia = obtener_sugerencia(
            descripcion=self.ticket.descripcion,
            categoria=categoria.nombre,
            servicio_afectado=servicio_afectado.nombre,
        )

        if sugerencia:
            self.ticket.prioridad_modelo = sugerencia["prioridad_predicha"]
            self.ticket.confianza_modelo = sugerencia["confianza"]
            # Registra si el operador aceptó la sugerencia en este momento.
            # Solo es recuperable ahora — no puede calcularse retroactivamente.
            self.ticket.siguio_sugerencia_ia = (
                prioridad_operador == sugerencia["prioridad_predicha"]
            )
        else:
            self.ticket.prioridad_modelo = None
            self.ticket.confianza_modelo = None
            self.ticket.siguio_sugerencia_ia = None

        self.ticket.save()

        detalle_clasificacion = (
            f'Categoría: {categoria}, Servicio: {servicio_afectado}, '
            f'Prioridad: {prioridad_operador}, SLA: {sla_horas}h'
        )
        self._registrar_bitacora(
            accion='Clasificación',
            detalle=detalle_clasificacion,
            valor_anterior=estado_anterior,
            valor_nuevo=Ticket.ESTADO_CLASIFICADO,
        )

        if sugerencia:
            self._registrar_bitacora(
                accion='Sugerencia IA',
                detalle=(
                    f'Modelo sugirió: {sugerencia["prioridad_predicha"]} '
                    f'(confianza: {sugerencia["confianza"]:.0%}). '
                    f'Operador {"aceptó" if self.ticket.siguio_sugerencia_ia else "no aceptó"} la sugerencia. '
                    f'Versión modelo: {sugerencia.get("version_modelo", "N/D")}'
                ),
                valor_anterior='',
                valor_nuevo=sugerencia["prioridad_predicha"],
            )
        else:
            self._registrar_bitacora(
                accion='Sugerencia IA no disponible',
                detalle='El servicio de predicción no respondió. Clasificación manual sin sugerencia.',
                valor_anterior='',
                valor_nuevo='',
            )


    def asignar(self, tecnico):
        """Clasificado → Asignado"""
        self._validar_transicion(Ticket.ESTADO_ASIGNADO)

        estado_anterior = self.ticket.estado
        tecnico_anterior = str(self.ticket.tecnico_asignado) if self.ticket.tecnico_asignado else 'Sin asignar'

        self.ticket.tecnico_asignado = tecnico
        self.ticket.estado = Ticket.ESTADO_ASIGNADO
        self.ticket.save()

        self._registrar_bitacora(
            accion='Asignación de técnico',
            detalle=f'Técnico asignado: {tecnico.get_full_name() or tecnico.username}',
            valor_anterior=tecnico_anterior,
            valor_nuevo=tecnico.get_full_name() or tecnico.username,
        )

    def tomar(self):
        """
        Asignado → En atención
        ÚNICA acción que estampa fecha_hora_primera_atencion.
        Solo el técnico asignado puede hacerlo.
        """
        if self.ticket.tecnico_asignado != self.usuario:
            raise PermissionDenied('Solo el técnico asignado puede tomar este ticket.')
        self._validar_transicion(Ticket.ESTADO_EN_ATENCION)

        estado_anterior = self.ticket.estado
        ahora = timezone.now()

        self.ticket.fecha_hora_primera_atencion = ahora
        self.ticket.estado = Ticket.ESTADO_EN_ATENCION
        self.ticket.save()

        self._registrar_bitacora(
            accion='Inicio de atención',
            detalle=f'Técnico {self.usuario.get_full_name() or self.usuario.username} tomó el ticket. TPA estampado: {ahora}',
            valor_anterior=estado_anterior,
            valor_nuevo=Ticket.ESTADO_EN_ATENCION,
        )

    def poner_en_espera(self, motivo):
        """En atención → En espera. Requiere motivo."""
        if self.ticket.tecnico_asignado != self.usuario:
            raise PermissionDenied('Solo el técnico asignado puede poner el ticket en espera.')
        self._validar_transicion(Ticket.ESTADO_EN_ESPERA)

        estado_anterior = self.ticket.estado
        self.ticket.estado = Ticket.ESTADO_EN_ESPERA
        self.ticket.save()

        self._registrar_bitacora(
            accion='Puesto en espera',
            detalle=f'Motivo: {motivo}',
            valor_anterior=estado_anterior,
            valor_nuevo=Ticket.ESTADO_EN_ESPERA,
        )

    def reanudar(self):
        """En espera → En atención"""
        if self.ticket.tecnico_asignado != self.usuario:
            raise PermissionDenied('Solo el técnico asignado puede reanudar el ticket.')
        self._validar_transicion(Ticket.ESTADO_EN_ATENCION)

        estado_anterior = self.ticket.estado
        self.ticket.estado = Ticket.ESTADO_EN_ATENCION
        self.ticket.save()

        self._registrar_bitacora(
            accion='Reanudación',
            detalle='Ticket reanudado desde estado En espera',
            valor_anterior=estado_anterior,
            valor_nuevo=Ticket.ESTADO_EN_ATENCION,
        )

    def resolver(self, solucion_aplicada):
        """
        En atención / En espera → Resuelto
        Requiere solucion_aplicada no vacío.
        Estampa fecha_hora_cierre provisional y calcula dentro_sla.
        """
        if self.ticket.tecnico_asignado != self.usuario:
            raise PermissionDenied('Solo el técnico asignado puede resolver el ticket.')
        self._validar_transicion(Ticket.ESTADO_RESUELTO)
        if not solucion_aplicada or not solucion_aplicada.strip():
            raise ValidationError('La solución aplicada es obligatoria para resolver el ticket.')

        estado_anterior = self.ticket.estado
        ahora = timezone.now()

        # Calcular dentro_sla
        self.ticket.solucion_aplicada = solucion_aplicada
        self.ticket.fecha_hora_cierre = ahora
        self.ticket.estado = Ticket.ESTADO_RESUELTO

        if self.ticket.sla_maximo_horas:
            delta = ahora - self.ticket.fecha_hora_registro
            horas = delta.total_seconds() / 3600
            self.ticket.dentro_sla = horas <= self.ticket.sla_maximo_horas
        else:
            self.ticket.dentro_sla = None

        self.ticket.save()

        self._registrar_bitacora(
            accion='Resolución',
            detalle=f'Solución: {solucion_aplicada[:200]}. Dentro del SLA: {self.ticket.dentro_sla}',
            valor_anterior=estado_anterior,
            valor_nuevo=Ticket.ESTADO_RESUELTO,
        )

    def cerrar(self):
        """Resuelto → Cerrado (manual por operador/admin)"""
        self._validar_transicion(Ticket.ESTADO_CERRADO)

        estado_anterior = self.ticket.estado
        self.ticket.estado = Ticket.ESTADO_CERRADO
        self.ticket.save()

        self._registrar_bitacora(
            accion='Cierre',
            detalle=f'Ticket cerrado por {self.usuario.get_full_name() or self.usuario.username}',
            valor_anterior=estado_anterior,
            valor_nuevo=Ticket.ESTADO_CERRADO,
        )

    def reabrir(self, descripcion_nueva):
        """
        Resuelto/Cerrado → crea un NUEVO Ticket con es_reapertura=True.
        No reutiliza el registro actual.
        El nuevo ticket comienza en estado 'Reabierto' (marcado como reapertura).
        """
        if self.ticket.estado not in [Ticket.ESTADO_RESUELTO, Ticket.ESTADO_CERRADO]:
            raise ValidationError('Solo se puede reabrir un ticket Resuelto o Cerrado.')

        nuevo_ticket = Ticket.objects.create(
            descripcion=descripcion_nueva,
            categoria=self.ticket.categoria,
            servicio_afectado=self.ticket.servicio_afectado,
            solicitante=self.usuario,
            estado=Ticket.ESTADO_REGISTRADO,
            es_reapertura=True,
            ticket_original=self.ticket,
        )

        # Registrar en la bitácora del ticket original
        self._registrar_bitacora(
            accion='Reapertura',
            detalle=f'Se creó nuevo ticket {nuevo_ticket.codigo} como reapertura',
            valor_anterior=self.ticket.estado,
            valor_nuevo=f'Reabierto → {nuevo_ticket.codigo}',
        )

        # Registrar en la bitácora del nuevo ticket
        BitacoraTicket.objects.create(
            ticket=nuevo_ticket,
            usuario=self.usuario,
            accion='Creación por reapertura',
            detalle=f'Reapertura del ticket {self.ticket.codigo}',
            valor_anterior='',
            valor_nuevo=Ticket.ESTADO_REGISTRADO,
        )

        return nuevo_ticket

    def actualizar_prioridad_correcta(self, prioridad_correcta):
        """
        Permite al administrador/operador registrar la prioridad_correcta
        para servir de ground truth al modelo ML en Fase 2.
        """
        valor_anterior = self.ticket.prioridad_correcta or 'Sin validar'
        self.ticket.prioridad_correcta = prioridad_correcta
        self.ticket.save()

        self._registrar_bitacora(
            accion='Validación de prioridad correcta',
            detalle=f'Prioridad correcta registrada: {prioridad_correcta}',
            valor_anterior=valor_anterior,
            valor_nuevo=prioridad_correcta,
        )
