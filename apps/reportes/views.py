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
        tpa_por_prioridad[prioridad] = (sum(tpa_lista) / len(tpa_lista)) if tpa_lista else None

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


def _inferir_impacto_urgencia(prioridad):
    """
    Mapeo de referencia ITIL estándar:
    Alta  -> Impacto: Alto, Urgencia: Alta
    Media -> Impacto: Medio, Urgencia: Media
    Baja  -> Impacto: Bajo, Urgencia: Baja
    """
    p = (prioridad or '').strip().capitalize()
    if p == 'Alta':
        return 'Alto', 'Alta'
    elif p == 'Media':
        return 'Medio', 'Media'
    elif p == 'Baja':
        return 'Bajo', 'Baja'
    return 'Medio', 'Media'


def _construir_fila_ticket(t):
    """
    Construye un diccionario con las 24 columnas completas del ticket,
    garantizando compatibilidad estricta con las 14 columnas canónicas de la tesis
    (dataset_completo.xlsx) y agregando los datos de Machine Learning y gestión operativa.
    Funciona para cualquier estado de la incidencia (nueva, en curso o cerrada).
    """
    ref_prio = t.prioridad_correcta or t.prioridad_operador or t.prioridad_modelo
    impacto, urgencia = _inferir_impacto_urgencia(ref_prio)

    if t.sla_maximo_horas:
        sla_max_h = t.sla_maximo_horas
    else:
        sla_max_h = 4 if ref_prio == 'Alta' else (24 if ref_prio == 'Media' else 72)

    tpa = t.calcular_horas_hasta_primera_atencion()
    if t.fecha_hora_registro and t.fecha_hora_cierre:
        delta = t.fecha_hora_cierre - t.fecha_hora_registro
        horas_trans = round(delta.total_seconds() / 3600, 2)
    elif t.fecha_hora_registro:
        delta = timezone.now() - t.fecha_hora_registro
        horas_trans = round(delta.total_seconds() / 3600, 2)
    else:
        horas_trans = 0.0

    if t.dentro_sla is not None:
        dentro_sla_str = 'Sí' if t.dentro_sla else 'No'
    elif t.fecha_hora_registro:
        dentro_sla_str = 'Sí' if horas_trans <= sla_max_h else 'No'
    else:
        dentro_sla_str = 'En curso'

    if t.prioridad_operador and t.prioridad_correcta:
        resultado = 'Correcto' if t.prioridad_operador == t.prioridad_correcta else 'Incorrecto'
    elif t.prioridad_operador:
        resultado = 'Sin validar'
    else:
        resultado = 'Pendiente'

    if t.confianza_modelo is not None:
        confianza_str = f"{round(t.confianza_modelo * 100, 2)}%"
    else:
        confianza_str = ''

    if t.siguio_sugerencia_ia is True:
        siguio_ia = 'Sí'
    elif t.siguio_sugerencia_ia is False:
        siguio_ia = 'No'
    elif t.prioridad_operador and t.prioridad_modelo:
        siguio_ia = 'Sí' if t.prioridad_operador == t.prioridad_modelo else 'No'
    else:
        siguio_ia = 'N/A'

    categoria_nombre = t.categoria.nombre if t.categoria else (
        t.servicio_afectado.categoria.nombre if (t.servicio_afectado and t.servicio_afectado.categoria) else ''
    )
    servicio_nombre = t.servicio_afectado.nombre if t.servicio_afectado else ''

    solicitante_str = (t.solicitante.get_full_name() or t.solicitante.username) if (getattr(t, 'solicitante_id', None) and t.solicitante) else ''
    tecnico_str = (t.tecnico_asignado.get_full_name() or t.tecnico_asignado.username) if (getattr(t, 'tecnico_asignado_id', None) and t.tecnico_asignado) else 'Sin asignar'

    codigo_ticket = f"TK-{t.pk:04d}" if t.pk else "TK-PENDIENTE"

    return {
        # ── 14 Columnas Canónicas de la Tesis (dataset_completo.xlsx) ──
        'ID Ticket': codigo_ticket,
        'Fecha registro': t.fecha_hora_registro.strftime('%Y-%m-%d %H:%M') if t.fecha_hora_registro else '',
        'Categoría': categoria_nombre,
        'Descripción': t.descripcion or '',
        'Servicio afectado': servicio_nombre,
        'Impacto': impacto,
        'Urgencia': urgencia,
        'Prioridad asignada (operador)': t.prioridad_operador or 'Sin clasificar',
        'Prioridad correcta (ITIL)': t.prioridad_correcta or 'Pendiente',
        'Fecha primera atención': t.fecha_hora_primera_atencion.strftime('%Y-%m-%d %H:%M') if t.fecha_hora_primera_atencion else 'Sin atención aún',
        'Horas transcurridas': horas_trans,
        'Resultado': resultado,
        'SLA máximo (h)': f"{sla_max_h}h",
        '¿Dentro del SLA?': dentro_sla_str,
        # ── Columnas Extendidas de Machine Learning y Gestión Operativa ──
        'Prioridad sugerida (Modelo ML)': t.prioridad_modelo or 'Sin sugerencia',
        'Confianza modelo (%)': confianza_str,
        '¿Siguió sugerencia IA?': siguio_ia,
        'Estado': t.estado,
        'Fecha cierre': t.fecha_hora_cierre.strftime('%Y-%m-%d %H:%M') if t.fecha_hora_cierre else 'En curso',
        'TPA (horas)': tpa if tpa is not None else '',
        'Solicitante': solicitante_str,
        'Técnico asignado': tecnico_str,
        'Solución aplicada': t.solucion_aplicada or '',
        '¿Es reapertura?': 'Sí' if t.es_reapertura else 'No',
    }


def _filtrar_tickets_para_exportacion(request):
    """
    Filtra los tickets para exportación asegurando que:
    1. Por defecto, exporta TODOS los tickets (sin excluir nuevos ni históricos).
    2. Si el usuario especificó rango en GET (?fecha_desde=...&fecha_hasta=...) y no pidió 'todo=1',
       aplica el filtro por fecha de registro.
    3. No excluye tickets incompletos o recién creados.
    """
    qs = Ticket.objects.all().select_related(
        'categoria', 'servicio_afectado', 'servicio_afectado__categoria',
        'solicitante', 'tecnico_asignado'
    ).order_by('pk')

    exportar_todo = request.GET.get('todo') in ['1', 'true', 'si'] or request.GET.get('todos') in ['1', 'true', 'si']
    fecha_desde_str = request.GET.get('fecha_desde', '').strip()
    fecha_hasta_str = request.GET.get('fecha_hasta', '').strip()

    if not exportar_todo and (fecha_desde_str or fecha_hasta_str):
        tz = timezone.get_current_timezone()
        if fecha_desde_str:
            try:
                f_desde = date.fromisoformat(fecha_desde_str)
                dt_desde = timezone.make_aware(datetime.combine(f_desde, datetime.min.time()), tz)
                qs = qs.filter(fecha_hora_registro__gte=dt_desde)
            except ValueError:
                pass
        if fecha_hasta_str:
            try:
                f_hasta = date.fromisoformat(fecha_hasta_str)
                dt_hasta = timezone.make_aware(datetime.combine(f_hasta, datetime.max.time().replace(microsecond=0)), tz)
                qs = qs.filter(fecha_hora_registro__lte=dt_hasta)
            except ValueError:
                pass

    if request.GET.get('excluir_reaperturas') == '1':
        qs = qs.filter(es_reapertura=False)

    return qs


@login_required
@requiere_rol('Administrador', 'Operador')
def exportar_excel(request):
    """Exporta todas las incidencias a Excel (.xlsx) con los 24 campos completos de la tesis y ML"""
    if not PANDAS_DISPONIBLE:
        from django.http import HttpResponseServerError
        return HttpResponseServerError('pandas/openpyxl no disponible.')

    qs = _filtrar_tickets_para_exportacion(request)
    filas = [_construir_fila_ticket(t) for t in qs]

    df = pd.DataFrame(filas)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dataset_Incidencias', index=False)

    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    fecha_desde_str = request.GET.get('fecha_desde', '').strip()
    fecha_hasta_str = request.GET.get('fecha_hasta', '').strip()
    if fecha_desde_str and fecha_hasta_str and request.GET.get('todo') != '1':
        nombre_archivo = f"dataset_incidencias_{fecha_desde_str}_{fecha_hasta_str}.xlsx"
    else:
        nombre_archivo = "dataset_completo_incidencias.xlsx"

    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


@login_required
@requiere_rol('Administrador', 'Operador')
def exportar_dataset_csv(request):
    """Exporta todas las incidencias a CSV (.csv) con los 24 campos completos de la tesis y ML"""
    qs = _filtrar_tickets_para_exportacion(request)
    filas = [_construir_fila_ticket(t) for t in qs]

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    fecha_desde_str = request.GET.get('fecha_desde', '').strip()
    fecha_hasta_str = request.GET.get('fecha_hasta', '').strip()
    if fecha_desde_str and fecha_hasta_str and request.GET.get('todo') != '1':
        nombre_archivo = f"dataset_incidencias_{fecha_desde_str}_{fecha_hasta_str}.csv"
    else:
        nombre_archivo = "dataset_completo_incidencias.csv"

    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    response.write('\ufeff')  # BOM UTF-8 para visualización directa en Excel

    if filas:
        fieldnames = list(filas[0].keys())
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        for fila in filas:
            writer.writerow(fila)
    else:
        dummy_fields = [
            'ID Ticket', 'Fecha registro', 'Categoría', 'Descripción', 'Servicio afectado',
            'Impacto', 'Urgencia', 'Prioridad asignada (operador)', 'Prioridad correcta (ITIL)',
            'Fecha primera atención', 'Horas transcurridas', 'Resultado', 'SLA máximo (h)',
            '¿Dentro del SLA?', 'Prioridad sugerida (Modelo ML)', 'Confianza modelo (%)',
            '¿Siguió sugerencia IA?', 'Estado', 'Fecha cierre', 'TPA (horas)',
            'Solicitante', 'Técnico asignado', 'Solución aplicada', '¿Es reapertura?'
        ]
        writer = csv.DictWriter(response, fieldnames=dummy_fields)
        writer.writeheader()

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


@login_required
@requiere_rol('Administrador', 'Operador')
def fichas_reportes(request):
    """
    Módulo de Reportes de Fichas (15 reportes periódicos de 3 días operarios cada uno)
    Muestra los 15 reportes en fila, con detalle interactivo breve.
    """
    PERIODOS_FICHAS = [
        (1, "2026-09-01", "2026-09-03", "01/09 al 03/09"),
        (2, "2026-09-04", "2026-09-07", "04/09 al 07/09"),
        (3, "2026-09-08", "2026-09-10", "08/09 al 10/09"),
        (4, "2026-09-11", "2026-09-14", "11/09 al 14/09"),
        (5, "2026-09-15", "2026-09-17", "15/09 al 17/09"),
        (6, "2026-09-18", "2026-09-21", "18/09 al 21/09"),
        (7, "2026-09-22", "2026-09-24", "22/09 al 24/09"),
        (8, "2026-09-25", "2026-09-28", "25/09 al 28/09"),
        (9, "2026-09-29", "2026-10-01", "29/09 al 01/10"),
        (10, "2026-10-02", "2026-10-05", "02/10 al 05/10"),
        (11, "2026-10-06", "2026-10-09", "06/10 al 09/10"),
        (12, "2026-10-10", "2026-10-13", "10/10 al 13/10"),
        (13, "2026-10-14", "2026-10-16", "14/10 al 16/10"),
        (14, "2026-10-17", "2026-10-20", "17/10 al 20/10"),
        (15, "2026-10-21", "2026-10-23", "21/10 al 23/10"),
    ]

    reportes = []
    total_general = 0

    for num, f_ini, f_fin, f_corta in PERIODOS_FICHAS:
        qs_periodo = Ticket.objects.filter(
            fecha_hora_registro__date__gte=f_ini,
            fecha_hora_registro__date__lte=f_fin
        ).select_related('categoria', 'servicio_afectado', 'solicitante', 'tecnico_asignado')

        ti = qs_periodo.count()
        total_general += ti

        # 1. TCC
        validados = qs_periodo.filter(prioridad_operador__isnull=False, prioridad_correcta__isnull=False)
        ic = validados.filter(prioridad_operador=F('prioridad_correcta')).count()
        tcc = round((ic / ti * 100), 2) if ti > 0 else 0.0

        # 2. Precision Alta
        asig_alta = qs_periodo.filter(prioridad_operador='Alta')
        total_alta = asig_alta.count()
        vp = asig_alta.filter(prioridad_correcta='Alta').count()
        fp = total_alta - vp
        prec_alta = round((vp / total_alta * 100), 2) if total_alta > 0 else 0.0

        # 3. TPA Crítico
        criticos = qs_periodo.filter(prioridad_correcta='Alta')
        tic = criticos.count()

        deltas = []
        for t in criticos:
            if t.fecha_hora_primera_atencion and t.fecha_hora_registro:
                deltas.append((t.fecha_hora_primera_atencion - t.fecha_hora_registro).total_seconds() / 3600.0)

        tpa_horas = round(sum(deltas) / len(deltas), 2) if deltas else 0.0
        tot_m = int(round(tpa_horas * 60))
        tpa_formato = f"{tot_m // 60}h {tot_m % 60:02d}min"

        # 4. TAO
        iat = criticos.filter(dentro_sla=True).count()
        tao = round((iat / tic * 100), 2) if tic > 0 else 0.0

        # Distribución de prioridades
        p_alta_cnt = qs_periodo.filter(prioridad_operador='Alta').count()
        p_media_cnt = qs_periodo.filter(prioridad_operador='Media').count()
        p_baja_cnt = qs_periodo.filter(prioridad_operador='Baja').count()

        # Top categorías
        cats = qs_periodo.values('categoria__nombre').annotate(cnt=Count('id')).order_by('-cnt')[:3]
        top_cats = [{'nombre': c['categoria__nombre'] or 'Sin categoría', 'cnt': c['cnt']} for c in cats]

        # Muestra rápida de hasta 5 incidencias para el breve detalle
        tickets_muestra = list(qs_periodo.order_by('id')[:5])

        reportes.append({
            'num': num,
            'num_fmt': f"{num:02d}",
            'fecha_corta': f_corta,
            'f_ini': f_ini,
            'f_fin': f_fin,
            'f_ini_fmt': datetime.strptime(f_ini, "%Y-%m-%d").strftime("%d/%m/%Y"),
            'f_fin_fmt': datetime.strptime(f_fin, "%Y-%m-%d").strftime("%d/%m/%Y"),
            'dias_operarios': 3,
            'ti': ti,
            'ic': ic,
            'tcc': tcc,
            'total_alta': total_alta,
            'vp': vp,
            'fp': fp,
            'prec_alta': prec_alta,
            'tic': tic,
            'tpa_horas': tpa_horas,
            'tpa_formato': tpa_formato,
            'iat': iat,
            'tao': tao,
            'p_alta': p_alta_cnt,
            'p_media': p_media_cnt,
            'p_baja': p_baja_cnt,
            'top_cats': top_cats,
            'tickets_muestra': tickets_muestra,
        })

    # Resumen global de los 15 reportes
    tcc_global = round(sum(r['tcc'] for r in reportes) / 15.0, 2)
    prec_alta_global = round(sum(r['prec_alta'] for r in reportes) / 15.0, 2)
    tpa_global = round(sum(r['tpa_horas'] for r in reportes) / 15.0, 2)
    tot_m_glob = int(round(tpa_global * 60))
    tpa_global_formato = f"{tot_m_glob // 60}h {tot_m_glob % 60:02d}min"
    tao_global = round(sum(r['tao'] for r in reportes) / 15.0, 2)

    context = {
        'reportes': reportes,
        'resumen': {
            'total_tickets': total_general,
            'promedio_tcc': tcc_global,
            'promedio_precision_alta': prec_alta_global,
            'promedio_tpa': tpa_global,
            'promedio_tpa_formato': tpa_global_formato,
            'promedio_tao': tao_global,
            'total_fichas': 15,
            'dias_operarios_total': 45,
        }
    }
    return render(request, 'reportes/fichas_reportes.html', context)
