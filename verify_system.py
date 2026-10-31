import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.template.loader import get_template
import traceback

templates = [
    'base.html',
    'usuarios/login.html',
    'tickets/bandeja.html',
    'tickets/detalle.html',
    'tickets/registrar.html',
    'tickets/partials/tabla_tickets.html',
    'reportes/dashboard.html',
    'reportes/bitacora.html',
    'catalogos/categorias.html',
    'catalogos/servicios.html',
    'catalogos/sla.html',
    'usuarios/gestion.html',
    'usuarios/perfil.html',
    'errors/404.html',
    'errors/500.html',
]

ok = 0
fail = 0
for t_name in templates:
    try:
        get_template(t_name)
        print(f'  OK  {t_name}')
        ok += 1
    except Exception as e:
        print(f'  FAIL {t_name}: {e}')
        fail += 1

print()
print(f'Resultado: {ok} OK, {fail} FAIL')
