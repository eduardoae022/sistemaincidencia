from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('fichas/', views.fichas_reportes, name='fichas_reportes'),
    path('exportar/excel/', views.exportar_excel, name='exportar_excel'),
    path('exportar/dataset/', views.exportar_dataset_csv, name='exportar_dataset'),
    path('bitacora/', views.bitacora_auditoria, name='bitacora'),
]
