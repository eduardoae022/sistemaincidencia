class VercelPathMiddleware:
    """
    Capa extra de seguridad en caso de que el PATH_INFO llegue con el prefijo
    /api/index.py al nivel de request de Django (doble blindaje).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path == '/api/index.py' or path.startswith('/api/index.py/'):
            cleaned = path[len('/api/index.py'):] or '/'
            request.path_info = cleaned
            request.path = cleaned
            request.META['PATH_INFO'] = cleaned
        return self.get_response(request)
