from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from apps.tickets.decorators import requiere_rol, get_rol_principal
from .forms import LoginForm, UsuarioCrearForm, UsuarioEditarForm, PerfilForm, CambiarPasswordForm
from .models import PerfilUsuario


def login_view(request):
    """Página de login del sistema"""
    if request.user.is_authenticated:
        return redirect('tickets:bandeja')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        next_url = request.GET.get('next', 'tickets:bandeja')
        return redirect(next_url)

    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    """Cerrar sesión"""
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('usuarios:login')


@login_required
def perfil_view(request):
    """Vista del perfil propio del usuario"""
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)

    if request.method == 'POST' and 'actualizar_perfil' in request.POST:
        form = PerfilForm(request.POST, instance=perfil, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('usuarios:perfil')
    else:
        form = PerfilForm(instance=perfil, user=request.user)

    pass_form = CambiarPasswordForm(request.user)

    return render(request, 'usuarios/perfil.html', {
        'form': form,
        'pass_form': pass_form,
        'perfil': perfil,
    })


@login_required
def cambiar_password_view(request):
    """Cambio de contraseña propio"""
    if request.method == 'POST':
        form = CambiarPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña actualizada correctamente.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
    return redirect('usuarios:perfil')


@login_required
@requiere_rol('Administrador')
def gestion_usuarios(request):
    """Panel de gestión de usuarios — solo Administrador"""
    from django.contrib.auth.models import Group
    usuarios = User.objects.prefetch_related('groups').order_by('last_name', 'first_name')
    form_crear = UsuarioCrearForm()
    grupos_disponibles = Group.objects.all().order_by('name')

    return render(request, 'usuarios/gestion.html', {
        'usuarios': usuarios,
        'form_crear': form_crear,
        'grupos_disponibles': grupos_disponibles,
    })


@login_required
@requiere_rol('Administrador')
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioCrearForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuario {user.username} creado exitosamente.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')
    return redirect('usuarios:gestion')


@login_required
@requiere_rol('Administrador')
def editar_usuario(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UsuarioEditarForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            rol = form.cleaned_data.get('rol')
            if rol:
                user.groups.set([rol])
            else:
                user.groups.clear()
            messages.success(request, f'Usuario {user.username} actualizado.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')
    return redirect('usuarios:gestion')
