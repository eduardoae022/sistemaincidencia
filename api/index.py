import os
import sys

# Agregar la raíz del proyecto al PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application as _get_wsgi

_inner = _get_wsgi()


class _VercelWSGI:
    """
    Wrapper WSGI que limpia el path interno de Vercel ANTES de que Django
    construya el HttpRequest y ejecute el URL resolver.

    Vercel envía PATH_INFO = '/api/index.py' (el script de la función)
    en lugar del path original que el usuario solicitó.
    Aquí lo normalizamos a '/' para que Django enrute correctamente.
    """

    def __init__(self, wsgi_app):
        self._app = wsgi_app

    def __call__(self, environ, start_response):
        # --- Limpiar path interno de Vercel ---
        path = environ.get('PATH_INFO', '/')
        if path == '/api/index.py' or path == '/api/index.py/':
            environ['PATH_INFO'] = '/'
        elif path.startswith('/api/index.py/'):
            environ['PATH_INFO'] = path[len('/api/index.py'):]
        elif path == '/api' or path == '/api/':
            environ['PATH_INFO'] = '/'
        elif path.startswith('/api/'):
            environ['PATH_INFO'] = path[len('/api'):]

        # --- Informar a Django que el proxy usa HTTPS ---
        environ['HTTP_X_FORWARDED_PROTO'] = 'https'
        environ['wsgi.url_scheme'] = 'https'

        return self._app(environ, start_response)


# Vercel busca una variable llamada 'app' que sea callable WSGI
app = _VercelWSGI(_inner)
