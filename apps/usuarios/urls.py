from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/password/', views.cambiar_password_view, name='cambiar_password'),
    path('gestion/', views.gestion_usuarios, name='gestion'),
    path('gestion/crear/', views.crear_usuario, name='crear_usuario'),
    path('gestion/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    # Recuperación de contraseña (backend de consola para desarrollo)
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='usuarios/password_reset.html'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='usuarios/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='usuarios/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='usuarios/password_reset_complete.html'
    ), name='password_reset_complete'),
]
