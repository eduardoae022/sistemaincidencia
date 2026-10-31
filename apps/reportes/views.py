"""
Vistas del módulo de reportes y dashboard.
Calcula KPIs de la tesis: TCC, TPA, TAO.
"""
import csv
import io
from datetime import date, timedelta, datetime

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Avg, Count, Q, F
from django.utils import timezone

from apps.tickets.models import Ticket
from apps.tickets.decorators import requiere_rol
from apps.catalogos.models import Categoria

try:
    import pandas as pd
    import openpyxl
    PANDAS_DISPONIBLE = True
except ImportError:
    PANDAS_DISPONIBLE = False


def _parsear_rango_fechas(request):
    """Extrae y valida el rango de fechas del request GET"""
    hoy = date.today()
    fecha_desde_str = request.GET.get('fecha_desde', '')
    fecha_hasta_str = request.GET.get('fecha_hasta', '')

    try:
        fecha_desde = date.fromisoformat(fecha_desde_str) if fecha_desde_str else hoy - timedelta(days=30)
        fecha_hasta = date.fromisoformat(fecha_hasta_str) if fecha_hasta_str else hoy
    except ValueError:
        fecha_desde = hoy - timedelta(days=30)
        fecha_hasta = hoy

    return fecha_desde, fecha_hasta


def _calcular_kpis(qs):
    """
    Calcula los KPIs principales de la tesis sobre un queryset de tickets.
    """
    total = qs.count()

    # ── TCC: Tasa de Clasificación Correcta ─────────────────────────────────
    # Tickets con prioridad_correcta registrada
    con_validacion = qs.filter(
        prioridad_operador__isnull=False,
        prioridad_correcta__isnull=False
    )
    total_validados = con_validacion.count()
    clasificados_correctamente = con_validacion.filter(
        prioridad_operador=F('prioridad_correcta')
    ).count()
    tcc = round((clasificados_correctamente / total_validados * 100), 2) if total_validados > 0 else None

    # ── TPA: Tiempo de Primera Atención por prioridad ────────────────────────
    tpa_por_prioridad = {}
    for prioridad in ['Alta', 'Media', 'Baja']:
        tickets_prio = qs.filter(
            prioridad_operador=prioridad,
            fecha_hora_primera_atencion__isnull=False
        )
        tpa_lista = []
        for t in tickets_prio:
            if t.fecha_hora_primera_atencion and t.fecha_hora_registro:
                delta = t.fecha_hora_primera_atencion - t.fecha_hora_registro
                tpa_lista.append(delta.total_seconds() / 3600)
        tpa_por_prioridad[prioridad] = round(sum(tpa_lista) / len(tpa_lista), 2) if tpa_lista else None

    # ── TAO: Tasa de Atención Oportuna ──────────────────────────────────────
    # Tickets cerrados/resueltos
    tickets_finalizados = qs.filter(
        estado__in=[Ticket.ESTADO_RESUELTO, Ticket.ESTADO_CERRADO],
        dentro_sla__isnull=False
    )
    total_finalizados = tickets_finalizados.count()
    dentro_sla = tickets_finalizados.filter(dentro_sla=True).count()
    tao = round((dentro_sla / total_finalizados * 100), 2) if total_finalizados > 0 else None

    # ── Distribuciones ───────────────────────────────────────────────────────
    por_estado = {}
    for estado_val, estado_label in Ticket.ESTADO_CHOICES:
        por_estado[estado_label] = qs.filter(estado=estado_val).count()

    por_prioridad = {}
    for p_val, p_label in Ticket.PRIORIDAD_CHOICES:
        por_prioridad[p_label] = qs.filter(prioridad_operador=p_val).count()
    por_prioridad['Sin clasificar'] = qs.filter(prioridad_operador__isnull=True).count()

    por_categoria = {}
    for cat in Categoria.objects.filter(activo=True):
        por_categoria[cat.nombre] = qs.filter(categoria=cat).count()

    return {
        'total': total,
        'tcc': tcc,
        'total_validados': total_validados,
        'clasificados_correctamente': clasificados_correctamente,
        'tpa_por_prioridad': tpa_por_prioridad,
        'tao': tao,
        'total_finalizados': total_finalizados,
        'dentro_sla': dentro_sla,
        'por_estado': por_estado,
        'por_prioridad': por_prioridad,
        'por_categoria': por_categoria,
    }


@login_required
@requiere_rol('Administrador', 'Operador')
def dashboard(request):
    """Dashboard con KPIs calculados sobre el rango de fechas seleccionado"""
    fecha_desde, fecha_hasta = _parsear_rango_fechas(request)

    # Convertir a datetime con timezone para compatibilidad con MySQL + USE_TZ=True
    tz = timezone.get_current_timezone()
    dt_desde = timezone.make_aware(datetime.combine(fecha_desde, datetime.min.time()), tz)
    dt_hasta = timezone.make_aware(datetime.combine(fecha_hasta, datetime.max.time().replace(microsecond=0)), tz)

    qs = Ticket.objects.filter(
        fecha_hora_registro__gte=dt_desde,
        fecha_hora_registro__lte=dt_hasta,
    )

    kpis = _calcular_kpis(qs)

    # Preparar datos para Chart.js (JSON-serializable)
    chart_estados_labels = list(kpis['por_estado'].keys())
    chart_estados_data = list(kpis['por_estado'].values())
    chart_prioridad_labels = list(kpis['por_prioridad'].keys())
    chart_prioridad_data = list(kpis['por_prioridad'].values())
    chart_categoria_labels = list(kpis['por_categoria'].keys())
    chart_categoria_data = list(kpis['por_categoria'].values())

    # Últimos 10 tickets para tabla resumen
    ultimos_tickets = Ticket.objects.select_related(
        'categoria', 'solicitante', 'tecnico_asignado'
    ).order_by('-fecha_hora_registro')[:10]

    context = {
        'kpis': kpis,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'chart_estados_labels': chart_estados_labels,
        'chart_estados_data': chart_estados_data,
        'chart_prioridad_labels': chart_prioridad_labels,
        'chart_prioridad_data': chart_prioridad_data,
        'chart_categoria_labels': chart_categoria_labels,
        'chart_categoria_data': chart_categoria_data,
        'ultimos_tickets': ultimos_tickets,
    }
    return render(request, 'reportes/dashboard.html', context)


@login_required
@requiere_rol('Administrador', 'Operador')
def exportar_excel(request):
    """Exporta el dashboard a Excel usando pandas + openpyxl"""
    if not PANDAS_DISPONIBLE:
        from django.http import HttpResponseServerError
        return HttpResponseServerError('pandas/openpyxl no disponible.')

    fecha_desde, fecha_hasta = _parsear_rango_fechas(request)
    tz = timezone.get_current_timezone()
    dt_desde = timezone.make_aware(datetime.combine(fecha_desde, datetime.min.time()), tz)
    dt_hasta = timezone.make_aware(datetime.combine(fecha_hasta, datetime.max.time().replace(microsecond=0)), tz)
    qs = Ticket.objects.filter(
        fecha_hora_registro__gte=dt_desde,
        fecha_hora_registro__lte=dt_hasta,
    ).select_related('categoria', 'servicio_afectado', 'solicitante', 'tecnico_asignado')

    # Construir DataFrame
    filas = []
    for t in qs:
        tpa = t.calcular_horas_hasta_primera_atencion()
        filas.append({
            'ID Ticket': t.codigo,
            'Estado': t.estado,
            'Categoría': t.categoria.nombre if t.categoria else '',
            'Servicio Afectado': str(t.servicio_afectado) if t.servicio_afectado else '',
            'Prioridad Operador': t.prioridad_operador or '',
            'Prioridad Correcta': t.prioridad_correcta or '',
            'Fecha Registro': t.fecha_hora_registro.strftime('%Y-%m-%d %H:%M') if t.fecha_hora_registro else '',
            'Fecha Primera Atención': t.fecha_hora_primera_atencion.strftime('%Y-%m-%d %H:%M') if t.fecha_hora_primera_atencion else '',
            'Fecha Cierre': t.fecha_hora_cierre.strftime('%Y-%m-%d %H:%M') if t.fecha_hora_cierre else '',
            'TPA (horas)': tpa if tpa is not None else '',
            'SLA Máximo (horas)': t.sla_maximo_horas or '',
            'Dentro SLA': ('Sí' if t.dentro_sla else 'No') if t.dentro_sla is not None else '',
            'Es Reapertura': 'Sí' if t.es_reapertura else 'No',
            'Técnico': t.tecnico_asignado.get_full_name() if t.tecnico_asignado else '',
            'Sugerencia de ML aplicada?': 'SI' if t.siguio_sugerencia_ia else 'NO',
        })

    df = pd.DataFrame(filas)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Tickets', index=False)

    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="reporte_tickets_{fecha_desde}_{fecha_hasta}.xlsx"'
    return response


@login_required
@requiere_rol('Administrador', 'Operador')
def exportar_dataset_csv(request):
    """
    Exporta el dataset para entrenamiento ML (Tabla 5 de la tesis).
    - Excluye reaperturas (es_reapertura=True)
    - Excluye tickets sin datos completos (sin prioridad_operador, sin cierre)
    - Anonimiza solicitante (solo ID interno)
    """
    excluir_reaperturas = request.GET.get('excluir_reaperturas', '1') == '1'
    solo_completos = request.GET.get('solo_completos', '1') == '1'
    fecha_desde, fecha_hasta = _parsear_rango_fechas(request)
    tz = timezone.get_current_timezone()
    dt_desde = timezone.make_aware(datetime.combine(fecha_desde, datetime.min.time()), tz)
    dt_hasta = timezone.make_aware(datetime.combine(fecha_hasta, datetime.max.time().replace(microsecond=0)), tz)

    qs = Ticket.objects.filter(
        fecha_hora_registro__gte=dt_desde,
        fecha_hora_registro__lte=dt_hasta,
    ).select_related('categoria', 'servicio_afectado')

    if excluir_reaperturas:
        qs = qs.filter(es_reapertura=False)

    if solo_completos:
        qs = qs.filter(
            prioridad_operador__isnull=False,
            fecha_hora_cierre__isnull=False,
            sla_maximo_horas__isnull=False,
            dentro_sla__isnull=False,
        )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="dataset_ml_{fecha_desde}_{fecha_hasta}.csv"'
    response.write('\ufeff')  # BOM para Excel

    writer = csv.writer(response)
    # Cabecera — Tabla 5 de la tesis
    writer.writerow([
        'id_ticket',
        'fecha_registro',
        'categoria',
        'servicio_afectado',
        'descripcion',
        'prioridad_operador',
        'prioridad_correcta',
        'horas_transcurridas',
        'sla_maximo_horas',
        'dentro_sla',
        'id_solicitante_anonimizado',  # Hash interno — sin nombre real
        'Sugerencia de ML aplicada?',
    ])

    for t in qs:
        if t.fecha_hora_registro and t.fecha_hora_cierre:
            delta = t.fecha_hora_cierre - t.fecha_hora_registro
            horas = round(delta.total_seconds() / 3600, 2)
        else:
            horas = ''

        # Anonimización: usar ID numérico, no nombre real
        id_anon = f'USR-{t.solicitante_id:04d}'

        writer.writerow([
            t.codigo,
            t.fecha_hora_registro.strftime('%Y-%m-%d %H:%M') if t.fecha_hora_registro else '',
            t.categoria.nombre if t.categoria else '',
            t.servicio_afectado.nombre if t.servicio_afectado else '',
            t.descripcion,
            t.prioridad_operador or '',
            t.prioridad_correcta or '',
            horas,
            t.sla_maximo_horas or '',
            ('1' if t.dentro_sla else '0') if t.dentro_sla is not None else '',
            id_anon,
            'SI' if t.siguio_sugerencia_ia else 'NO',
        ])

    return response


@login_required
@requiere_rol('Administrador')
def bitacora_auditoria(request):
    """Vista de solo lectura de la bitácora completa — solo Administrador"""
    from apps.tickets.models import BitacoraTicket
    from django.contrib.auth.models import User as UserModel

    qs = BitacoraTicket.objects.select_related('ticket', 'usuario').order_by('-fecha_hora')

    # Filtros
    ticket_id = request.GET.get('ticket', '')
    usuario_id = request.GET.get('usuario', '')
    fecha_desde_str = request.GET.get('fecha_desde', '')
    fecha_hasta_str = request.GET.get('fecha_hasta', '')

    if ticket_id:
        qs = qs.filter(ticket__pk=ticket_id.replace('TK-', '').strip())
    if usuario_id:
        qs = qs.filter(usuario__pk=usuario_id)
    if fecha_desde_str:
        try:
            qs = qs.filter(fecha_hora__date__gte=date.fromisoformat(fecha_desde_str))
        except ValueError:
            pass
    if fecha_hasta_str:
        try:
            qs = qs.filter(fecha_hora__date__lte=date.fromisoformat(fecha_hasta_str))
        except ValueError:
            pass

    usuarios = UserModel.objects.filter(is_active=True).order_by('last_name', 'first_name')

    context = {
        'registros': qs[:500],  # límite para rendimiento
        'usuarios': usuarios,
        'filtros': {
            'ticket': ticket_id,
            'usuario': usuario_id,
            'fecha_desde': fecha_desde_str,
            'fecha_hasta': fecha_hasta_str,
        }
    }
    return render(request, 'reportes/bitacora.html', context)
