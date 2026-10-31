from django import forms
from django.contrib.auth.models import User
from apps.catalogos.models import Categoria, ServicioAfectado
from .models import Ticket, Comentario


class TicketRegistroForm(forms.ModelForm):
    """Formulario para solicitante — solo descripción y servicio"""

    class Meta:
        model = Ticket
        fields = ['descripcion', 'servicio_afectado']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describa detalladamente el problema, síntomas, cuándo ocurrió y el impacto en sus actividades...',
                'id': 'id_descripcion',
            }),
            'servicio_afectado': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_servicio_afectado',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio_afectado'].queryset = ServicioAfectado.objects.filter(
            activo=True
        ).select_related('categoria')
        self.fields['servicio_afectado'].empty_label = '— Seleccione el servicio afectado —'
        self.fields['descripcion'].label = 'Descripción de la incidencia'
        self.fields['servicio_afectado'].label = 'Servicio afectado'


class TicketClasificacionForm(forms.Form):
    """Formulario para operador — clasificación de la incidencia"""
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(activo=True),
        label='Categoría',
        empty_label='— Seleccione categoría —',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_cat_clasif'}),
    )
    servicio_afectado = forms.ModelChoiceField(
        queryset=ServicioAfectado.objects.filter(activo=True).select_related('categoria'),
        label='Servicio afectado',
        empty_label='— Seleccione servicio —',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_serv_clasif'}),
    )
    prioridad_operador = forms.ChoiceField(
        choices=[('', '— Seleccione prioridad —')] + Ticket.PRIORIDAD_CHOICES,
        label='Prioridad',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_prioridad_clasif'}),
    )

    def clean_prioridad_operador(self):
        valor = self.cleaned_data.get('prioridad_operador')
        if not valor:
            raise forms.ValidationError('Debe seleccionar una prioridad.')
        return valor


class TicketAsignacionForm(forms.Form):
    """Formulario para operador — asignación de técnico"""
    tecnico = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Técnico de soporte',
        empty_label='— Seleccione técnico —',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_tecnico'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import Group
        try:
            grupo_tecnicos = Group.objects.get(name='Técnico')
            self.fields['tecnico'].queryset = grupo_tecnicos.user_set.filter(
                is_active=True
            ).order_by('first_name', 'last_name')
        except Group.DoesNotExist:
            pass


class TicketEsperaForm(forms.Form):
    """Formulario para técnico — poner en espera con motivo"""
    motivo = forms.CharField(
        label='Motivo de la espera',
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Indique qué información o acción está esperando del solicitante...',
            'id': 'id_motivo_espera',
        }),
    )


class TicketResolucionForm(forms.Form):
    """Formulario para técnico — resolución del ticket"""
    solucion_aplicada = forms.CharField(
        label='Solución aplicada',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Describa la solución aplicada, pasos realizados y resultado obtenido...',
            'id': 'id_solucion',
        }),
    )

    def clean_solucion_aplicada(self):
        valor = self.cleaned_data.get('solucion_aplicada', '').strip()
        if not valor:
            raise forms.ValidationError('La descripción de la solución es obligatoria.')
        if len(valor) < 20:
            raise forms.ValidationError('La solución debe tener al menos 20 caracteres.')
        return valor


class TicketPrioridadCorrectaForm(forms.Form):
    """Para validar la prioridad correcta (ground truth para ML)"""
    prioridad_correcta = forms.ChoiceField(
        choices=[('', '— Seleccione —')] + Ticket.PRIORIDAD_CHOICES,
        label='Prioridad correcta',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_prioridad_correcta'}),
    )

    def clean_prioridad_correcta(self):
        valor = self.cleaned_data.get('prioridad_correcta')
        if not valor:
            raise forms.ValidationError('Debe seleccionar la prioridad correcta.')
        return valor


class TicketReaperturaForm(forms.Form):
    """Formulario para reabrir un ticket"""
    descripcion = forms.CharField(
        label='Descripción del nuevo problema',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Describa el nuevo problema o por qué la solución anterior no fue efectiva...',
            'id': 'id_desc_reapertura',
        }),
    )


class ComentarioForm(forms.ModelForm):
    """Hilo de comentarios del ticket"""

    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escriba su comentario o consulta aquí...',
                'id': 'id_comentario_texto',
            }),
        }
        labels = {'texto': 'Comentario'}


class TicketFiltroForm(forms.Form):
    """Formulario de filtros para la bandeja de tickets"""
    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + Ticket.ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'filtro_estado'}),
    )
    prioridad = forms.ChoiceField(
        choices=[('', 'Todas las prioridades')] + Ticket.PRIORIDAD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'filtro_prioridad'}),
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(activo=True),
        required=False,
        empty_label='Todas las categorías',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'filtro_categoria'}),
    )
    tecnico = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        empty_label='Todos los técnicos',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'filtro_tecnico'}),
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date',
            'id': 'filtro_fecha_desde',
        }),
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date',
            'id': 'filtro_fecha_hasta',
        }),
    )
    buscar = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Buscar por TK-XXXX o descripción...',
            'id': 'filtro_buscar',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import Group
        try:
            grupo_tecnicos = Group.objects.get(name='Técnico')
            self.fields['tecnico'].queryset = grupo_tecnicos.user_set.filter(
                is_active=True
            ).order_by('first_name', 'last_name')
        except Group.DoesNotExist:
            pass
