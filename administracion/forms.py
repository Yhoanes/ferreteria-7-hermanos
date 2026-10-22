from django import forms
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import EmpresaConfig, Usuario


class BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class UsuarioForm(BootstrapFormMixin, forms.ModelForm):
    contrasena = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        required=False,
    )

    class Meta:
        model = Usuario
        fields = ["nombre", "correo", "rol"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "maxlength": 150,
                "required": True,
                "autocomplete": "name",
            }),
            "correo": forms.EmailInput(attrs={
                "required": True,
                "autocomplete": "email",
            }),
        }

    def __init__(self, *args, require_password=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rol"].queryset = Group.objects.all().order_by("name")
        self.fields["rol"].required = False
        self.fields["contrasena"].required = require_password

        if not require_password:
            self.fields["contrasena"].help_text = "Dejar en blanco para conservar la contraseña actual."

        self._apply_bootstrap()

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()

        if not nombre:
            raise ValidationError("El nombre del usuario es obligatorio.")

        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")

        return nombre

    def clean_correo(self):
        correo = self.cleaned_data.get("correo", "").strip().lower()

        if not correo:
            raise ValidationError("El correo del usuario es obligatorio.")

        existe = Usuario.objects.filter(correo__iexact=correo)

        if self.instance and self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)

        if existe.exists():
            raise ValidationError("Ya existe un usuario registrado con este correo.")

        return correo

    def clean_contrasena(self):
        contrasena = self.cleaned_data.get("contrasena")

        if not contrasena:
            return contrasena

        validate_password(contrasena)

        return contrasena

    def clean(self):
        cleaned_data = super().clean()
        contrasena = cleaned_data.get("contrasena")

        if contrasena:
            self.instance.contrasena = make_password(contrasena)

        return cleaned_data


class EmpresaConfigForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = EmpresaConfig
        fields = ["nombre", "nit", "telefono", "direccion"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "maxlength": 100,
                "required": True,
                "autocomplete": "organization",
            }),
            "nit": forms.TextInput(attrs={
                "maxlength": 50,
                "required": True,
                "inputmode": "numeric",
                "pattern": r"[0-9]+",
            }),
            "telefono": forms.TextInput(attrs={
                "maxlength": 50,
                "required": True,
                "inputmode": "tel",
                "pattern": r"[0-9+\-\s]+",
                "autocomplete": "tel",
            }),
            "direccion": forms.TextInput(attrs={
                "maxlength": 255,
                "required": True,
                "autocomplete": "street-address",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()

        if not nombre:
            raise ValidationError("El nombre de la empresa es obligatorio.")

        if len(nombre) < 3:
            raise ValidationError("El nombre de la empresa debe tener al menos 3 caracteres.")

        return nombre

    def clean_nit(self):
        nit = self.cleaned_data.get("nit", "").strip()

        if not nit:
            raise ValidationError("El NIT es obligatorio.")

        if not nit.isdigit():
            raise ValidationError("El NIT solo debe contener números.")

        if len(nit) < 5:
            raise ValidationError("El NIT debe tener al menos 5 dígitos.")

        return nit

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono", "").strip()

        if not telefono:
            raise ValidationError("El teléfono es obligatorio.")

        caracteres_validos = telefono.replace("+", "").replace(" ", "").replace("-", "")

        if not caracteres_validos.isdigit():
            raise ValidationError("El teléfono solo debe contener números, espacios, + o guiones.")

        if len(caracteres_validos) < 7:
            raise ValidationError("El teléfono debe tener al menos 7 dígitos.")

        return telefono

    def clean_direccion(self):
        direccion = self.cleaned_data.get("direccion", "").strip()

        if not direccion:
            raise ValidationError("La dirección es obligatoria.")

        if len(direccion) < 5:
            raise ValidationError("La dirección debe tener al menos 5 caracteres.")

        return direccion