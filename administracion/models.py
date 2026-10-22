from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models


def _strip_or_empty(value):
    return (value or "").strip()


class Usuario(models.Model):
    nombre = models.CharField(max_length=150)
    correo = models.EmailField(unique=True)
    contrasena = models.CharField(max_length=128)

    # Rol del usuario (Administrador, Vendedor, etc.)
    rol = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def clean(self):
        self.nombre = _strip_or_empty(self.nombre)
        self.correo = _strip_or_empty(self.correo).lower()

        errors = {}

        if not self.nombre:
            errors["nombre"] = "El nombre del usuario es obligatorio."

        if not self.correo:
            errors["correo"] = "El correo del usuario es obligatorio."

        if not self.contrasena:
            errors["contrasena"] = "La contraseña es obligatoria."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.nombre


class EmpresaConfig(models.Model):
    nombre = models.CharField(
        max_length=100,
        default="Ferreteria 7 Hermanos"
    )

    nit = models.CharField(
        max_length=50,
        default="1234567015"
    )

    telefono = models.CharField(
        max_length=50,
        default="+591 70000000"
    )

    direccion = models.CharField(
        max_length=255,
        default="Direccion Principal, Santa Cruz de la Sierra"
    )

    # Usuario que realizó la última modificación
    actualizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="configuraciones_actualizadas",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Configuración de la Empresa"
        verbose_name_plural = "Configuración de la Empresa"

    def clean(self):
        self.nombre = _strip_or_empty(self.nombre)
        self.nit = _strip_or_empty(self.nit)
        self.telefono = _strip_or_empty(self.telefono)
        self.direccion = _strip_or_empty(self.direccion)

        errors = {}

        if not self.nombre:
            errors["nombre"] = "El nombre de la empresa es obligatorio."

        if not self.nit:
            errors["nit"] = "El NIT es obligatorio."

        if not self.telefono:
            errors["telefono"] = "El teléfono es obligatorio."
        elif not self.telefono.replace("+", "").replace(" ", "").replace("-", "").isdigit():
            errors["telefono"] = "El teléfono solo debe contener números, espacios, + o guiones."

        if not self.direccion:
            errors["direccion"] = "La dirección es obligatoria."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.nombre