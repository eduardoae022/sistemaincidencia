from django import forms
from .models import Categoria, ServicioAfectado, SLA


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_cat_nombre'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_cat_activo'}),
        }


class ServicioAfectadoForm(forms.ModelForm):
    class Meta:
        model = ServicioAfectado
        fields = ['nombre', 'categoria', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_serv_nombre'}),
            'categoria': forms.Select(attrs={'class': 'form-select', 'id': 'id_serv_cat'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_serv_activo'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.filter(activo=True)


class SLAForm(forms.ModelForm):
    class Meta:
        model = SLA
        fields = ['prioridad', 'horas_maximas']
        widgets = {
            'prioridad': forms.Select(attrs={'class': 'form-select', 'id': 'id_sla_prioridad'}),
            'horas_maximas': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'id': 'id_sla_horas'
            }),
        }
