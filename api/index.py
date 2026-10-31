import os
import sys

# Agregar la raíz del proyecto al path para que Django encuentre config, apps, etc.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
_django_app = get_wsgi_application()


def app(environ, start_response):
    """
    Punto de entrada Serverless para Vercel.
    
    Vercel envía todas las peticiones a esta función. La URL interna de Vercel
    contiene '/api/index.py' o similar como PATH_INFO. Aquí normalizamos eso
    para que Django reciba rutas limpias como '/', '/tickets/', '/usuarios/login/'
    sin intermediarios que causen bucles de redirección.
    """
    path_info = environ.get('PATH_INFO', '/')
    
    # Vercel puede enviar el script como prefijo — lo limpiamos
    for prefix in ('/api/index.py', '/api'):
        if path_info.startswith(prefix):
            environ['PATH_INFO'] = path_info[len(prefix):] or '/'
            break

    # Indicar a Django que estamos detrás de HTTPS (proxy de Vercel)
    environ.setdefault('HTTP_X_FORWARDED_PROTO', 'https')
    environ.setdefault('wsgi.url_scheme', 'https')

    return _django_app(environ, start_response)
