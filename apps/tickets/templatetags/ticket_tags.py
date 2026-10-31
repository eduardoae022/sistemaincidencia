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


@register.simple_tag
def get_rol_tag(user):
    """Version simple_tag de get_rol para usar con {% %}"""
    return get_rol(user)

