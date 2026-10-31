from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.bandeja, name='bandeja'),
    path('nuevo/', views.registrar_ticket, name='registrar'),
    path('<int:pk>/', views.detalle_ticket, name='detalle'),
    path('<int:pk>/clasificar/', views.clasificar_ticket, name='clasificar'),
    path('<int:pk>/asignar/', views.asignar_ticket, name='asignar'),
    path('<int:pk>/tomar/', views.tomar_ticket, name='tomar'),
    path('<int:pk>/espera/', views.poner_en_espera, name='espera'),
    path('<int:pk>/reanudar/', views.reanudar_ticket, name='reanudar'),
    path('<int:pk>/resolver/', views.resolver_ticket, name='resolver'),
    path('<int:pk>/cerrar/', views.cerrar_ticket, name='cerrar'),
    path('<int:pk>/reabrir/', views.reabrir_ticket, name='reabrir'),
    path('<int:pk>/comentar/', views.agregar_comentario, name='comentar'),
    path('<int:pk>/prioridad-correcta/', views.registrar_prioridad_correcta, name='prioridad_correcta'),
]
