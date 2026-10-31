from django.contrib import admin
from .models import Categoria, ServicioAfectado, SLA


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre']


class ServicioAfectadoInline(admin.TabularInline):
    model = ServicioAfectado
    extra = 1
    fields = ['nombre', 'activo']


@admin.register(ServicioAfectado)
class ServicioAfectadoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'activo']
    list_filter = ['categoria', 'activo']
    search_fields = ['nombre']


@admin.register(SLA)
class SLAAdmin(admin.ModelAdmin):
    list_display = ['prioridad', 'horas_maximas']
    ordering = ['prioridad']
