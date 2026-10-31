from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuarios/', include('apps.usuarios.urls', namespace='usuarios')),
    path('tickets/', include('apps.tickets.urls', namespace='tickets')),
    path('catalogos/', include('apps.catalogos.urls', namespace='catalogos')),
    path('reportes/', include('apps.reportes.urls', namespace='reportes')),
    path('', include('apps.tickets.urls_home')),
]

handler404 = 'apps.tickets.views.handler404'
handler500 = 'apps.tickets.views.handler500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
