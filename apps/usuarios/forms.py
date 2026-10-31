from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import PerfilUsuario


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre de usuario',
            'autofocus': True,
            'id': 'id_username',
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Contraseña',
            'id': 'id_password',
        })
    )


class UsuarioCrearForm(forms.ModelForm):
    """Formulario para crear usuarios desde el panel de administrador"""
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_pass1'}),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_pass2'}),
    )
    rol = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label='Rol',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_rol'}),
        empty_label='— Seleccione rol —',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_uname'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_fname'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_lname'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_email'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            user.groups.set([self.cleaned_data['rol']])
            PerfilUsuario.objects.get_or_create(usuario=user)
        return user


class UsuarioEditarForm(forms.ModelForm):
    """Editar datos básicos del usuario"""
    rol = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label='Rol',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_edit_rol'}),
        empty_label='— Sin rol —',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_edit_fname'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_edit_lname'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_edit_email'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            grupos = self.instance.groups.all()
            if grupos.exists():
                self.fields['rol'].initial = grupos.first()


class PerfilForm(forms.ModelForm):
    """Editar perfil propio"""
    first_name = forms.CharField(
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_perfil_fname'}),
    )
    last_name = forms.CharField(
        label='Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_perfil_lname'}),
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_perfil_email'}),
    )

    class Meta:
        model = PerfilUsuario
        fields = ['telefono', 'area']
        widgets = {
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_perfil_tel'}),
            'area': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_perfil_area'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        perfil = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            if commit:
                self.user.save()
                perfil.save()
        return perfil


class CambiarPasswordForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Contraseña actual',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_old_pass'}),
    )
    new_password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_new_pass1'}),
    )
    new_password2 = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'id_new_pass2'}),
    )
