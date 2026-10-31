from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import PerfilUsuario


class PerfilInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'


class UsuarioAdmin(UserAdmin):
    inlines = [PerfilInline]


# Re-register UserAdmin con el perfil inlineado
admin.site.unregister(User)
admin.site.register(User, UsuarioAdmin)
admin.site.register(PerfilUsuario)
