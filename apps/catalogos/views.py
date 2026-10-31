from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.tickets.decorators import requiere_rol
from .models import Categoria, ServicioAfectado, SLA
from .forms import CategoriaForm, ServicioAfectadoForm, SLAForm


# ── Categorías ───────────────────────────────────────────────────────────────

@login_required
@requiere_rol('Administrador')
def lista_categorias(request):
    categorias = Categoria.objects.all().order_by('nombre')
    form = CategoriaForm()
    return render(request, 'catalogos/categorias.html', {
        'categorias': categorias, 'form': form
    })


@login_required
@requiere_rol('Administrador')
def crear_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada exitosamente.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')
    return redirect('catalogos:categorias')


@login_required
@requiere_rol('Administrador')
def editar_categoria(request, pk):
    cat = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, f'Categoría "{cat.nombre}" actualizada.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')
    return redirect('catalogos:categorias')


# ── Servicios afectados ──────────────────────────────────────────────────────

@login_required
@requiere_rol('Administrador')
def lista_servicios(request):
    servicios = ServicioAfectado.objects.select_related('categoria').order_by('categoria__nombre', 'nombre')
    categorias = Categoria.objects.filter(activo=True).order_by('nombre')
    form = ServicioAfectadoForm()
    return render(request, 'catalogos/servicios.html', {
        'servicios': servicios, 'form': form, 'categorias': categorias
    })


@login_required
@requiere_rol('Administrador')
def crear_servicio(request):
    if request.method == 'POST':
        form = ServicioAfectadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio afectado creado.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')
    return redirect('catalogos:servicios')


@login_required
@requiere_rol('Administrador')
def editar_servicio(request, pk):
    serv = get_object_or_404(ServicioAfectado, pk=pk)
    if request.method == 'POST':
        form = ServicioAfectadoForm(request.POST, instance=serv)
        if form.is_valid():
            form.save()
            messages.success(request, f'Servicio "{serv.nombre}" actualizado.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')
    return redirect('catalogos:servicios')


# ── SLA ──────────────────────────────────────────────────────────────────────

@login_required
@requiere_rol('Administrador')
def lista_sla(request):
    slas = SLA.objects.all().order_by('prioridad')
    form = SLAForm()
    return render(request, 'catalogos/sla.html', {'slas': slas, 'form': form})


@login_required
@requiere_rol('Administrador')
def editar_sla(request, pk):
    sla = get_object_or_404(SLA, pk=pk)
    if request.method == 'POST':
        form = SLAForm(request.POST, instance=sla)
        if form.is_valid():
            form.save()
            messages.success(request, f'SLA para prioridad {sla.prioridad} actualizado a {sla.horas_maximas}h.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')
    return redirect('catalogos:sla')
