"""
Vistas para el módulo de tickets.
Toda transición de estado pasa por TicketStateMachine.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, F
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime

from .models import Ticket, BitacoraTicket, Comentario
from .forms import (
    TicketRegistroForm, TicketClasificacionForm, TicketAsignacionForm,
    TicketEsperaForm, TicketResolucionForm, TicketReaperturaForm,
    ComentarioForm, TicketFiltroForm, TicketPrioridadCorrectaForm,
)
from .state_machine import TicketStateMachine
from .decorators import requiere_rol, get_rol_principal
from .prediccion_client import obtener_sugerencia



# ── Utilidades ───────────────────────────────────────────────────────────────

def _get_queryset_por_rol(user):
    """Filtra el queryset de tickets según el rol del usuario"""
    rol = get_rol_principal(user)
    qs = Ticket.objects.select_related(
        'categoria', 'servicio_afectado', 'solicitante', 'tecnico_asignado'
    )
    if rol == 'Solicitante':
        return qs.filter(solicitante=user)
    elif rol == 'Técnico':
        return qs.filter(tecnico_asignado=user)
    else:  # Operador, Administrador, superusuario
        return qs.all()


# ── Bandeja de tickets ───────────────────────────────────────────────────────

@login_required
def bandeja(request):
    """Vista principal de bandeja — filtrable por estado, prioridad, categoría, etc."""
    rol = get_rol_principal(request.user)
    qs = _get_queryset_por_rol(request.user)
    form = TicketFiltroForm(request.GET or None)

    if form.is_valid():
        if form.cleaned_data.get('estado'):
            qs = qs.filter(estado=form.cleaned_data['estado'])
        if form.cleaned_data.get('prioridad'):
            qs = qs.filter(prioridad_operador=form.cleaned_data['prioridad'])
        if form.cleaned_data.get('categoria'):
            qs = qs.filter(categoria=form.cleaned_data['categoria'])
        if form.cleaned_data.get('tecnico') and rol != 'Solicitante':
            qs = qs.filter(tecnico_asignado=form.cleaned_data['tecnico'])
        if form.cleaned_data.get('fecha_desde'):
            tz = timezone.get_current_timezone()
            dt = timezone.make_aware(datetime.combine(form.cleaned_data['fecha_desde'], datetime.min.time()), tz)
            qs = qs.filter(fecha_hora_registro__gte=dt)
        if form.cleaned_data.get('fecha_hasta'):
            tz = timezone.get_current_timezone()
            dt = timezone.make_aware(datetime.combine(form.cleaned_data['fecha_hasta'], datetime.max.time().replace(microsecond=0)), tz)
            qs = qs.filter(fecha_hora_registro__lte=dt)
        if form.cleaned_data.get('buscar'):
            buscar = form.cleaned_data['buscar']
            # Buscar por código TK-XXXX o descripción
            qs = qs.filter(
                Q(descripcion__icontains=buscar) |
                Q(pk__icontains=buscar.replace('TK-', '').replace('tk-', '').strip())
            )

    # Filtro rápido de Clasificación Correcta (IC) para la tesis
    filtro_ic = request.GET.get('filtro_ic', '').strip().lower()
    if filtro_ic == 'correcto':
        qs = qs.filter(prioridad_operador=F('prioridad_correcta')).exclude(prioridad_correcta__isnull=True)
    elif filtro_ic == 'incorrecto':
        qs = qs.exclude(prioridad_operador=F('prioridad_correcta')).exclude(prioridad_correcta__isnull=True)

    tickets = qs.order_by('-fecha_hora_registro')

    # Métricas globales de Clasificación Correcta (TCC)
    base_qs = _get_queryset_por_rol(request.user)
    total_eval = base_qs.exclude(prioridad_correcta__isnull=True).exclude(prioridad_operador__isnull=True).count()
    total_corr = base_qs.filter(prioridad_operador=F('prioridad_correcta')).exclude(prioridad_correcta__isnull=True).count()
    total_incorr = total_eval - total_corr
    tcc_global = round((total_corr / total_eval * 100), 1) if total_eval > 0 else 0

    # Calcular métricas SLA y verificación de acierto ITIL para cada ticket
    tickets_con_sla = []
    for t in tickets:
        es_correcto = None
        if t.prioridad_operador and t.prioridad_correcta:
            es_correcto = (t.prioridad_operador == t.prioridad_correcta)
        tickets_con_sla.append({
            'ticket': t,
            'sla_restante': t.calcular_sla_restante_horas(),
            'estado_sla': t.estado_sla(),
            'horas_transcurridas': round(t.calcular_horas_transcurridas(), 1),
            'es_correcto': es_correcto,
        })

    context = {
        'tickets_con_sla': tickets_con_sla,
        'form': form,
        'rol': rol,
        'total': len(tickets_con_sla),
        'total_eval': total_eval,
        'total_corr': total_corr,
        'total_incorr': total_incorr,
        'tcc_global': tcc_global,
        'filtro_ic': filtro_ic,
    }

    # Si es una petición HTMX, devolver solo la tabla
    if request.htmx:
        return render(request, 'tickets/partials/tabla_tickets.html', context)

    return render(request, 'tickets/bandeja.html', context)


# ── Registro de ticket ───────────────────────────────────────────────────────

@login_required
def registrar_ticket(request):
    """El solicitante crea un nuevo ticket"""
    if request.method == 'POST':
        form = TicketRegistroForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.solicitante = request.user
            ticket.estado = Ticket.ESTADO_REGISTRADO
            # La categoría se infiere del servicio elegido
            ticket.categoria = ticket.servicio_afectado.categoria
            ticket.save()

            # Registrar en bitácora
            BitacoraTicket.objects.create(
                ticket=ticket,
                usuario=request.user,
                accion='Registro de incidencia',
                detalle=f'Ticket registrado por {request.user.get_full_name() or request.user.username}',
                valor_anterior='',
                valor_nuevo=Ticket.ESTADO_REGISTRADO,
            )

            messages.success(
                request,
                f'✅ Incidencia registrada exitosamente. Su número de ticket es <strong>{ticket.codigo}</strong>.'
            )
            return redirect('tickets:detalle', pk=ticket.pk)
    else:
        form = TicketRegistroForm()

    return render(request, 'tickets/registrar.html', {'form': form})


# ── Detalle de ticket ────────────────────────────────────────────────────────

@login_required
def detalle_ticket(request, pk):
    """Vista de detalle con historial, comentarios y acciones según rol"""
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            'categoria', 'servicio_afectado', 'solicitante',
            'tecnico_asignado', 'ticket_original'
        ),
        pk=pk
    )
    rol = get_rol_principal(request.user)

    # Control de acceso: solicitante solo ve sus propios tickets
    if rol == 'Solicitante' and ticket.solicitante != request.user:
        raise PermissionDenied
    # Técnico solo ve sus tickets asignados
    if rol == 'Técnico' and ticket.tecnico_asignado != request.user:
        raise PermissionDenied

    bitacora = ticket.bitacora.all().order_by('fecha_hora')
    comentarios = ticket.comentarios.all().select_related('usuario').order_by('fecha_hora')
    comment_form = ComentarioForm()

    # Formularios de acción (se muestran solo si aplican)
    clasif_form = TicketClasificacionForm(initial={
        'categoria': ticket.categoria,
        'servicio_afectado': ticket.servicio_afectado,
        'prioridad_operador': ticket.prioridad_operador,
    }) if ticket.estado == Ticket.ESTADO_REGISTRADO else None

    # Sugerencia IA previa: si el ticket está Registrado y tiene servicio/categoría,
    # consultar al modelo para mostrar la recomendación al operador ANTES de que clasifique.
    sugerencia_previa = None
    if ticket.estado == Ticket.ESTADO_REGISTRADO and ticket.servicio_afectado and ticket.categoria:
        sugerencia_previa = obtener_sugerencia(
            descripcion=ticket.descripcion,
            categoria=ticket.categoria.nombre,
            servicio_afectado=ticket.servicio_afectado.nombre,
        )

    asign_form = TicketAsignacionForm(initial={
        'tecnico': ticket.tecnico_asignado,
    }) if ticket.estado == Ticket.ESTADO_CLASIFICADO else None

    espera_form = TicketEsperaForm() if ticket.estado == Ticket.ESTADO_EN_ATENCION else None
    resol_form = TicketResolucionForm() if ticket.estado in [
        Ticket.ESTADO_EN_ATENCION, Ticket.ESTADO_EN_ESPERA
    ] else None
    reab_form = TicketReaperturaForm() if ticket.estado in [
        Ticket.ESTADO_RESUELTO, Ticket.ESTADO_CERRADO
    ] else None
    prio_correcta_form = TicketPrioridadCorrectaForm(
        initial={'prioridad_correcta': ticket.prioridad_correcta}
    ) if rol in ['Administrador', 'Operador'] else None

    reaperturas = ticket.reaperturas.all()

    context = {
        'ticket': ticket,
        'rol': rol,
        'bitacora': bitacora,
        'comentarios': comentarios,
        'comment_form': comment_form,
        'clasif_form': clasif_form,
        'asign_form': asign_form,
        'espera_form': espera_form,
        'resol_form': resol_form,
        'reab_form': reab_form,
        'prio_correcta_form': prio_correcta_form,
        'reaperturas': reaperturas,
        'sla_restante': ticket.calcular_sla_restante_horas(),
        'estado_sla': ticket.estado_sla(),
        'tpa_horas': ticket.calcular_horas_hasta_primera_atencion(),
        # Sugerencia IA persistida (posterior a clasificación)
        'tiene_sugerencia_ia': ticket.prioridad_modelo is not None,
        # Sugerencia IA previa (para mostrar en el formulario ANTES de clasificar)
        'sugerencia_previa': sugerencia_previa,
    }
    return render(request, 'tickets/detalle.html', context)




# ── Acciones de comentario ───────────────────────────────────────────────────

@login_required
def agregar_comentario(request, pk):
    """POST — agrega un comentario al ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    rol = get_rol_principal(request.user)

    if rol == 'Solicitante' and ticket.solicitante != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.ticket = ticket
            comentario.usuario = request.user
            comentario.save()

            BitacoraTicket.objects.create(
                ticket=ticket,
                usuario=request.user,
                accion='Comentario',
                detalle=comentario.texto[:200],
                valor_anterior='',
                valor_nuevo='',
            )
            messages.success(request, 'Comentario agregado.')
        else:
            messages.error(request, 'Error al agregar el comentario.')

    return redirect('tickets:detalle', pk=pk)


# ── Transiciones de estado ───────────────────────────────────────────────────

@login_required
@requiere_rol('Administrador', 'Operador')
def clasificar_ticket(request, pk):
    """Registrado → Clasificado"""
    ticket = get_object_or_404(Ticket, pk=pk, estado=Ticket.ESTADO_REGISTRADO)

    if request.method == 'POST':
        form = TicketClasificacionForm(request.POST)
        if form.is_valid():
            try:
                sm = TicketStateMachine(ticket, request.user)
                sm.clasificar(
                    categoria=form.cleaned_data['categoria'],
                    servicio_afectado=form.cleaned_data['servicio_afectado'],
                    prioridad_operador=form.cleaned_data['prioridad_operador'],
                )
                messages.success(request, f'Ticket {ticket.codigo} clasificado correctamente.')
            except (ValidationError, Exception) as e:
                messages.error(request, f'Error: {e}')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')

    return redirect('tickets:detalle', pk=pk)


@login_required
@requiere_rol('Administrador', 'Operador')
def asignar_ticket(request, pk):
    """Clasificado → Asignado"""
    ticket = get_object_or_404(Ticket, pk=pk, estado=Ticket.ESTADO_CLASIFICADO)

    if request.method == 'POST':
        form = TicketAsignacionForm(request.POST)
        if form.is_valid():
            try:
                sm = TicketStateMachine(ticket, request.user)
                sm.asignar(tecnico=form.cleaned_data['tecnico'])
                messages.success(request, f'Ticket {ticket.codigo} asignado a {form.cleaned_data["tecnico"]}.')
            except (ValidationError, PermissionDenied, Exception) as e:
                messages.error(request, f'Error: {e}')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')

    return redirect('tickets:detalle', pk=pk)


@login_required
@requiere_rol('Administrador', 'Técnico')
def tomar_ticket(request, pk):
    """
    Asignado → En atención.
    ÚNICA acción que estampa fecha_hora_primera_atencion.
    Solo el técnico asignado puede hacerlo.
    """
    ticket = get_object_or_404(Ticket, pk=pk, estado=Ticket.ESTADO_ASIGNADO)

    if request.method == 'POST':
        try:
            sm = TicketStateMachine(ticket, request.user)
            sm.tomar()
            messages.success(request, f'Ticket {ticket.codigo} tomado. Hora de primera atención registrada.')
        except (PermissionDenied, ValidationError, Exception) as e:
            messages.error(request, f'Error: {e}')

    return redirect('tickets:detalle', pk=pk)


@login_required
@requiere_rol('Administrador', 'Técnico')
def poner_en_espera(request, pk):
    """En atención → En espera"""
    ticket = get_object_or_404(Ticket, pk=pk, estado=Ticket.ESTADO_EN_ATENCION)

    if request.method == 'POST':
        form = TicketEsperaForm(request.POST)
        if form.is_valid():
            try:
                sm = TicketStateMachine(ticket, request.user)
                sm.poner_en_espera(motivo=form.cleaned_data['motivo'])
                messages.success(request, f'Ticket {ticket.codigo} puesto en espera.')
            except (PermissionDenied, ValidationError, Exception) as e:
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'Debe ingresar el motivo de la espera.')

    return redirect('tickets:detalle', pk=pk)


@login_required
@requiere_rol('Administrador', 'Técnico')
def reanudar_ticket(request, pk):
    """En espera → En atención"""
    ticket = get_object_or_404(Ticket, pk=pk, estado=Ticket.ESTADO_EN_ESPERA)

    if request.method == 'POST':
        try:
            sm = TicketStateMachine(ticket, request.user)
            sm.reanudar()
            messages.success(request, f'Ticket {ticket.codigo} reanudado.')
        except (PermissionDenied, ValidationError, Exception) as e:
            messages.error(request, f'Error: {e}')

    return redirect('tickets:detalle', pk=pk)


@login_required
@requiere_rol('Administrador', 'Técnico')
def resolver_ticket(request, pk):
    """En atención / En espera → Resuelto"""
    ticket = get_object_or_404(
        Ticket, pk=pk,
        estado__in=[Ticket.ESTADO_EN_ATENCION, Ticket.ESTADO_EN_ESPERA]
    )

    if request.method == 'POST':
        form = TicketResolucionForm(request.POST)
        if form.is_valid():
            try:
                sm = TicketStateMachine(ticket, request.user)
                sm.resolver(solucion_aplicada=form.cleaned_data['solucion_aplicada'])
                messages.success(request, f'Ticket {ticket.codigo} resuelto exitosamente.')
            except (PermissionDenied, ValidationError, Exception) as e:
                messages.error(request, f'Error: {e}')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')

    return redirect('tickets:detalle', pk=pk)


@login_required
@requiere_rol('Administrador', 'Operador')
def cerrar_ticket(request, pk):
    """Resuelto → Cerrado (manual)"""
    ticket = get_object_or_404(Ticket, pk=pk, estado=Ticket.ESTADO_RESUELTO)

    if request.method == 'POST':
        try:
            sm = TicketStateMachine(ticket, request.user)
            sm.cerrar()
            messages.success(request, f'Ticket {ticket.codigo} cerrado definitivamente.')
        except (ValidationError, Exception) as e:
            messages.error(request, f'Error: {e}')

    return redirect('tickets:detalle', pk=pk)


@login_required
def reabrir_ticket(request, pk):
    """Resuelto/Cerrado → nuevo ticket con es_reapertura=True"""
    ticket = get_object_or_404(
        Ticket, pk=pk,
        estado__in=[Ticket.ESTADO_RESUELTO, Ticket.ESTADO_CERRADO]
    )
    rol = get_rol_principal(request.user)

    # Solo el solicitante original o admin/operador pueden reabrir
    if rol == 'Solicitante' and ticket.solicitante != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = TicketReaperturaForm(request.POST)
        if form.is_valid():
            try:
                sm = TicketStateMachine(ticket, request.user)
                nuevo = sm.reabrir(descripcion_nueva=form.cleaned_data['descripcion'])
                messages.success(
                    request,
                    f'Reapertura creada. Nuevo ticket: <strong>{nuevo.codigo}</strong>.'
                )
                return redirect('tickets:detalle', pk=nuevo.pk)
            except (ValidationError, Exception) as e:
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'La descripción es obligatoria.')

    return redirect('tickets:detalle', pk=pk)


@login_required
@requiere_rol('Administrador', 'Operador')
def registrar_prioridad_correcta(request, pk):
    """Registra la prioridad_correcta como ground truth para el ML"""
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.method == 'POST':
        form = TicketPrioridadCorrectaForm(request.POST)
        if form.is_valid():
            try:
                sm = TicketStateMachine(ticket, request.user)
                sm.actualizar_prioridad_correcta(
                    prioridad_correcta=form.cleaned_data['prioridad_correcta']
                )
                messages.success(request, 'Prioridad correcta registrada.')
            except Exception as e:
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'Error al registrar la prioridad.')

    return redirect('tickets:detalle', pk=pk)


# ── Páginas de error ─────────────────────────────────────────────────────────

def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    return render(request, 'errors/500.html', status=500)
