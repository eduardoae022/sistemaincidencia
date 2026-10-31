"""
Decoradores de roles para controlar el acceso según grupos de Django.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def requiere_rol(*roles):
    """
    Decorador que verifica que el usuario pertenezca a al menos uno de los roles dados.
    Uso: @requiere_rol('Administrador', 'Operador')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            grupos_usuario = set(request.user.groups.values_list('name', flat=True))
            if not grupos_usuario.intersection(set(roles)):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def es_administrador(view_func):
    return requiere_rol('Administrador')(view_func)


def es_operador(view_func):
    return requiere_rol('Administrador', 'Operador')(view_func)


def es_tecnico(view_func):
    return requiere_rol('Administrador', 'Técnico')(view_func)


def es_solicitante(view_func):
    return requiere_rol('Administrador', 'Operador', 'Técnico', 'Solicitante')(view_func)


def get_rol_principal(user):
    """Retorna el rol principal del usuario (string) para lógica de templates"""
    if user.is_superuser:
        return 'Administrador'
    grupos = list(user.groups.values_list('name', flat=True))
    for rol in ['Administrador', 'Operador', 'Técnico', 'Solicitante']:
        if rol in grupos:
            return rol
    return None
