import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

_django_app = get_wsgi_application()

def app(environ, start_response):
    # Vercel rewrites pasan '/api/index.py' en PATH_INFO. 
    # Normalizamos el path para que Django reciba la ruta original del navegador.
    path_info = environ.get('PATH_INFO', '')
    if path_info.startswith('/api/index.py'):
        environ['PATH_INFO'] = path_info[len('/api/index.py'):] or '/'
    elif path_info.startswith('/api'):
        environ['PATH_INFO'] = path_info[len('/api'):] or '/'
    
    return _django_app(environ, start_response)
