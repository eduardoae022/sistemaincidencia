import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

def app(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'application/json; charset=utf-8')]
    start_response(status, response_headers)
    
    # Extraer variables clave de environ
    debug_info = {
        'PATH_INFO': environ.get('PATH_INFO'),
        'REQUEST_URI': environ.get('REQUEST_URI'),
        'RAW_URI': environ.get('RAW_URI'),
        'HTTP_X_FORWARDED_URI': environ.get('HTTP_X_FORWARDED_URI'),
        'HTTP_X_INVOKE_PATH': environ.get('HTTP_X_INVOKE_PATH'),
        'HTTP_X_MATCHED_PATH': environ.get('HTTP_X_MATCHED_PATH'),
        'SCRIPT_NAME': environ.get('SCRIPT_NAME'),
        'QUERY_STRING': environ.get('QUERY_STRING'),
        'HTTP_HOST': environ.get('HTTP_HOST'),
        'ALL_HTTP_HEADERS': {k: v for k, v in environ.items() if k.startswith('HTTP_') or k.startswith('x_') or 'PATH' in k or 'URI' in k}
    }
    return [json.dumps(debug_info, indent=2).encode('utf-8')]
