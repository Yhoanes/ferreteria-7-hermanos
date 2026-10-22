from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower


def _strip_or_empty(value):
    return (value or "").strip()


telefono_validator = RegexValidator(
    regex=r"^[0-9+\-\s]+$",
    message="El teléfono solo debe contener números, espacios, + o guiones.",
)


class Categoria(models.Model):
    nombre = models.CharField(
        max_length=100,
        validators=[MaxLengthValidator(100)],
    )
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                Lower("nombre"),
                name="categoria_nombre_unico_ci",
            ),
        ]

    def clean(self):
        super().clean()

        self.nombre = _strip_or_empty(self.nombre)
        self.descripcion = _strip_or_empty(self.descripcion)

        errors = {}

        if not self.nombre:
            errors["nombre"] = "El nombre de la categoría es obligatorio."
        elif len(self.nombre) < 3:
            errors["nombre"] = "El nombre de la categoría debe tener al menos 3 caracteres."
        else:
            existe = Categoria.objects.filter(nombre__iexact=self.nombre)
            if self.pk:
                existe = existe.exclude(pk=self.pk)
            if existe.exists():
                errors["nombre"] = "Ya existe una categoría con este nombre."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    nombre = models.CharField(
        max_length=100,
        validators=[MaxLengthValidator(100)],
    )
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "marca"
        verbose_name_plural = "marcas"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                Lower("nombre"),
                name="marca_nombre_unico_ci",
            ),
        ]

    def clean(self):
        super().clean()

        self.nombre = _strip_or_empty(self.nombre)
        self.descripcion = _strip_or_empty(self.descripcion)

        errors = {}

        if not self.nombre:
            errors["nombre"] = "El nombre de la marca es obligatorio."
        elif len(self.nombre) < 2:
            errors["nombre"] = "El nombre de la marca debe tener al menos 2 caracteres."
        else:
            existe = Marca.objects.filter(nombre__iexact=self.nombre)
            if self.pk:
                existe = existe.exclude(pk=self.pk)
            if existe.exists():
                errors["nombre"] = "Ya existe una marca con este nombre."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    nombre_empresa = models.CharField(
        max_length=150,
        validators=[MaxLengthValidator(150)],
    )
    contacto = models.CharField(
        max_length=100,
        validators=[MaxLengthValidator(100)],
    )
    telefono = models.CharField(
        max_length=20,
        validators=[MaxLengthValidator(20), telefono_validator],
    )
    direccion = models.CharField(
        max_length=255,
        validators=[MaxLengthValidator(255)],
    )

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["nombre_empresa"]
        indexes = [
            models.Index(fields=["nombre_empresa"]),
            models.Index(fields=["telefono"]),
        ]

    def clean(self):
        super().clean()

        self.nombre_empresa = _strip_or_empty(self.nombre_empresa)
        self.contacto = _strip_or_empty(self.contacto)
        self.telefono = _strip_or_empty(self.telefono)
        self.direccion = _strip_or_empty(self.direccion)

        errors = {}

        if not self.nombre_empresa:
            errors["nombre_empresa"] = "El nombre de la empresa es obligatorio."
        elif len(self.nombre_empresa) < 3:
            errors["nombre_empresa"] = "El nombre de la empresa debe tener al menos 3 caracteres."

        if not self.contacto:
            errors["contacto"] = "El contacto del proveedor es obligatorio."
        elif len(self.contacto) < 3:
            errors["contacto"] = "El contacto debe tener al menos 3 caracteres."

        if not self.telefono:
            errors["telefono"] = "El teléfono del proveedor es obligatorio."
        else:
            telefono_limpio = self.telefono.replace("+", "").replace(" ", "").replace("-", "")
            if not telefono_limpio.isdigit():
                errors["telefono"] = "El teléfono solo debe contener números, espacios, + o guiones."
            elif len(telefono_limpio) < 7:
                errors["telefono"] = "El teléfono debe tener al menos 7 dígitos."

        if not self.direccion:
            errors["direccion"] = "La dirección del proveedor es obligatoria."
        elif len(self.direccion) < 5:
            errors["direccion"] = "La dirección debe tener al menos 5 caracteres."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.nombre_empresa


class Producto(models.Model):
    codigo = models.CharField(
        max_length=50,
        unique=True,
        validators=[MaxLengthValidator(50)],
    )
    nombre = models.CharField(
        max_length=150,
        validators=[MaxLengthValidator(150)],
    )
    descripcion = models.TextField(blank=True, null=True)

    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    stock_actual = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    stock_minimo = models.IntegerField(
        default=5,
        validators=[MinValueValidator(0)],
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.RESTRICT,
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.RESTRICT,
    )

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["nombre"]),
            models.Index(fields=["activo"]),
            models.Index(fields=["categoria"]),
            models.Index(fields=["proveedor"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(precio_compra__gte=0),
                name="producto_precio_compra_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(precio_venta__gte=0),
                name="producto_precio_venta_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(precio_venta__gte=F("precio_compra")),
                name="producto_precio_venta_mayor_igual_compra",
            ),
            models.CheckConstraint(
                condition=Q(stock_actual__gte=0),
                name="producto_stock_actual_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(stock_minimo__gte=0),
                name="producto_stock_minimo_no_negativo",
            ),
        ]

    def clean(self):
        super().clean()

        self.codigo = _strip_or_empty(self.codigo).upper()
        self.nombre = _strip_or_empty(self.nombre)
        self.descripcion = _strip_or_empty(self.descripcion)

        errors = {}

        if not self.codigo:
            errors["codigo"] = "El código del producto es obligatorio."
        elif len(self.codigo) < 2:
            errors["codigo"] = "El código del producto debe tener al menos 2 caracteres."
        else:
            existe = Producto.objects.filter(codigo__iexact=self.codigo)
            if self.pk:
                existe = existe.exclude(pk=self.pk)
            if existe.exists():
                errors["codigo"] = "Ya existe un producto con este código."

        if not self.nombre:
            errors["nombre"] = "El nombre del producto es obligatorio."
        elif len(self.nombre) < 3:
            errors["nombre"] = "El nombre del producto debe tener al menos 3 caracteres."

        if self.precio_compra is None:
            errors["precio_compra"] = "El precio de compra es obligatorio."
        elif self.precio_compra < Decimal("0.00"):
            errors["precio_compra"] = "El precio de compra no puede ser negativo."

        if self.precio_venta is None:
            errors["precio_venta"] = "El precio de venta es obligatorio."
        elif self.precio_venta < Decimal("0.00"):
            errors["precio_venta"] = "El precio de venta no puede ser negativo."

        if self.precio_compra is not None and self.precio_venta is not None:
            if self.precio_venta < self.precio_compra:
                errors["precio_venta"] = "El precio de venta no puede ser menor al precio de compra."

        if self.stock_actual is None:
            errors["stock_actual"] = "El stock actual es obligatorio."
        elif self.stock_actual < 0:
            errors["stock_actual"] = "El stock actual no puede ser negativo."

        if self.stock_minimo is None:
            errors["stock_minimo"] = "El stock mínimo es obligatorio."
        elif self.stock_minimo < 0:
            errors["stock_minimo"] = "El stock mínimo no puede ser negativo."

        if not self.categoria_id:
            errors["categoria"] = "La categoría del producto es obligatoria."

        if not self.proveedor_id:
            errors["proveedor"] = "El proveedor del producto es obligatorio."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"