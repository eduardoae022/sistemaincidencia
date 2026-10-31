from django.contrib import admin
from .models import Ticket, BitacoraTicket, Comentario


class BitacoraInline(admin.TabularInline):
    model = BitacoraTicket
    extra = 0
    readonly_fields = ['usuario', 'accion', 'detalle', 'valor_anterior', 'valor_nuevo', 'fecha_hora']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0
    readonly_fields = ['usuario', 'texto', 'fecha_hora']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'estado', 'prioridad_operador', 'categoria',
        'solicitante', 'tecnico_asignado', 'dentro_sla', 'fecha_hora_registro'
    ]
    list_filter = ['estado', 'prioridad_operador', 'categoria', 'dentro_sla', 'es_reapertura']
    search_fields = ['pk', 'descripcion', 'solicitante__username']
    readonly_fields = [
        'fecha_hora_registro', 'fecha_hora_primera_atencion',
        'fecha_hora_cierre', 'dentro_sla', 'sla_maximo_horas',
        'prioridad_modelo', 'confianza_modelo',  # Reservados para Fase 2
    ]
    inlines = [BitacoraInline, ComentarioInline]

    fieldsets = (
        ('Información básica', {
            'fields': ('descripcion', 'categoria', 'servicio_afectado', 'solicitante')
        }),
        ('Clasificación y asignación', {
            'fields': ('prioridad_operador', 'prioridad_correcta', 'estado', 'tecnico_asignado')
        }),
        ('SLA', {
            'fields': ('sla_maximo_horas', 'dentro_sla')
        }),
        ('Tiempos', {
            'fields': ('fecha_hora_registro', 'fecha_hora_primera_atencion', 'fecha_hora_cierre')
        }),
        ('Resolución', {
            'fields': ('solucion_aplicada',)
        }),
        ('Reapertura', {
            'fields': ('es_reapertura', 'ticket_original')
        }),
        ('Fase 2 — Machine Learning (no usar aún)', {
            'fields': ('prioridad_modelo', 'confianza_modelo'),
            'classes': ('collapse',),
        }),
    )


@admin.register(BitacoraTicket)
class BitacoraTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'usuario', 'accion', 'fecha_hora']
    list_filter = ['accion', 'fecha_hora']
    search_fields = ['ticket__pk', 'usuario__username', 'detalle']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'usuario', 'fecha_hora']
    readonly_fields = ['fecha_hora']
