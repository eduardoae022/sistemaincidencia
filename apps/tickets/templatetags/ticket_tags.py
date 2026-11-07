from django import template

register = template.Library()


@register.filter
def get_rol(user):
    """Retorna el rol principal del usuario para uso en templates"""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'Administrador'
    grupos = list(user.groups.values_list('name', flat=True))
    for rol in ['Administrador', 'Operador', 'Técnico', 'Solicitante']:
        if rol in grupos:
            return rol
    return None


@register.filter
def estado_css(estado):
    """Convierte el estado del ticket a clase CSS"""
    mapa = {
        'Registrado': 'estado-registrado',
        'Clasificado': 'estado-clasificado',
        'Asignado': 'estado-asignado',
        'En atención': 'estado-en-atencion',
        'En espera': 'estado-en-espera',
        'Resuelto': 'estado-resuelto',
        'Cerrado': 'estado-cerrado',
        'Reabierto': 'estado-reabierto',
    }
    return mapa.get(estado, 'estado-registrado')


@register.filter
def prioridad_css(prioridad):
    """Convierte la prioridad a clase CSS"""
    mapa = {
        'Alta': 'prioridad-alta',
        'Media': 'prioridad-media',
        'Baja': 'prioridad-baja',
    }
    return mapa.get(prioridad, 'prioridad-none')


@register.filter
def sla_css(estado_sla):
    """Clase CSS para el indicador SLA"""
    return f'sla-{estado_sla}' if estado_sla else 'sla-sin_sla'


@register.filter
def porcentaje(valor):
    """Convierte un float (ej: 0.604) en porcentaje entero (ej: 60)"""
    if valor is None:
        return '0'
    try:
        val_float = float(valor)
        # Si ya viene en escala 0-100 (ej: 60.4)
        if val_float > 1.0:
            return str(round(val_float))
        # Si viene en escala 0.0 a 1.0 (ej: 0.604)
        return str(round(val_float * 100))
    except (ValueError, TypeError):
        return '0'


@register.filter
def formato_tiempo(valor):
    """
    Convierte una cantidad de horas (decimal o float) a formato legible en horas y minutos (60 min = 1h).
    Ejemplos:
      2.9  -> "2h 54min" (0.9h * 60 = 54min)
      0.5  -> "30min"
      1.0  -> "1h"
      0.0  -> "0min"
      None -> "—"
    """
    if valor is None:
        return "—"
    try:
        val_float = float(valor)
        signo = "-" if val_float < 0 else ""
        total_minutos = int(round(abs(val_float) * 60))
        h = total_minutos // 60
        m = total_minutos % 60
        if h > 0 and m > 0:
            return f"{signo}{h}h {m}min"
        elif h > 0:
            return f"{signo}{h}h"
        else:
            return f"{signo}{m}min"
    except (ValueError, TypeError):
        return str(valor)


@register.filter
def formato_tiempo_abs(valor):
    """Retorna formato_tiempo en valor absoluto (sin signo negativo)"""
    if valor is None:
        return "—"
    try:
        return formato_tiempo(abs(float(valor)))
    except (ValueError, TypeError):
        return str(valor)


@register.simple_tag
def get_rol_tag(user):
    """Version simple_tag de get_rol para usar con {% %}"""
    return get_rol(user)

