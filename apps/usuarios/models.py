from django.db import models
from django.contrib.auth.models import User


class PerfilUsuario(models.Model):
    """Perfil extendido de usuario — información adicional"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    area = models.CharField(max_length=100, blank=True, verbose_name='Área/Departamento')

    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuarios'

    def __str__(self):
        return f'Perfil de {self.usuario.get_full_name() or self.usuario.username}'
