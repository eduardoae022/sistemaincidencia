from django.urls import path
from . import views

app_name = 'catalogos'

urlpatterns = [
    path('categorias/', views.lista_categorias, name='categorias'),
    path('categorias/nueva/', views.crear_categoria, name='crear_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    path('servicios/', views.lista_servicios, name='servicios'),
    path('servicios/nuevo/', views.crear_servicio, name='crear_servicio'),
    path('servicios/<int:pk>/editar/', views.editar_servicio, name='editar_servicio'),
    path('sla/', views.lista_sla, name='sla'),
    path('sla/<int:pk>/editar/', views.editar_sla, name='editar_sla'),
]
