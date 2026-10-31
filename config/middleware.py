class VercelPathMiddleware:
    """
    Middleware para Vercel Serverless.
    Elimina el prefijo interno '/api/index.py' o '/api' del path para que Django
    resuelva las URLs normales (/tickets/, /usuarios/login/, /admin/, etc.).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path.startswith('/api/index.py'):
            request.path_info = path[len('/api/index.py'):] or '/'
        elif path.startswith('/api'):
            request.path_info = path[len('/api'):] or '/'
        
        return self.get_response(request)
