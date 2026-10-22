from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from administracion.models import Usuario
from producto.models import Producto


def _strip_or_none(value):
    value = (value or "").strip()
    return value or None


def _strip_or_empty(value):
    return (value or "").strip()


class Cliente(models.Model):
    nombre = models.CharField(
        max_length=150,
        validators=[MaxLengthValidator(150)],
    )
    documento_identidad = models.CharField(
        max_length=50,
        validators=[MaxLengthValidator(50)],
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[MaxLengthValidator(20)],
    )
    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        validators=[MaxLengthValidator(255)],
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre", "id"]
        indexes = [
            models.Index(fields=["nombre"], name="cliente_nombre_idx"),
            models.Index(fields=["documento_identidad"], name="cliente_documento_idx"),
            models.Index(fields=["activo"], name="cliente_activo_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["documento_identidad"],
                name="cliente_documento_unico",
            ),
        ]

    def clean(self):
        super().clean()

        self.nombre = _strip_or_empty(self.nombre)
        self.documento_identidad = _strip_or_empty(self.documento_identidad)
        self.telefono = _strip_or_none(self.telefono)
        self.direccion = _strip_or_none(self.direccion)

        errors = {}

        if not self.nombre:
            errors["nombre"] = "El nombre del cliente es obligatorio."
        elif len(self.nombre) < 3:
            errors["nombre"] = "El nombre del cliente debe tener al menos 3 caracteres."

        if not self.documento_identidad:
            errors["documento_identidad"] = "El documento de identidad es obligatorio."
        elif len(self.documento_identidad) < 3:
            errors["documento_identidad"] = "El documento de identidad debe tener al menos 3 caracteres."

        if self.telefono:
            telefono_limpio = self.telefono.replace("+", "").replace(" ", "").replace("-", "")
            if not telefono_limpio.isdigit():
                errors["telefono"] = "El teléfono solo debe contener números, espacios, + o guiones."
            elif len(telefono_limpio) < 7:
                errors["telefono"] = "El teléfono debe tener al menos 7 números."

        if self.direccion and len(self.direccion) < 5:
            errors["direccion"] = "La dirección debe tener al menos 5 caracteres."

        duplicado = Cliente.objects.filter(
            documento_identidad__iexact=self.documento_identidad
        ).exclude(pk=self.pk).exists()

        if self.documento_identidad and duplicado:
            errors["documento_identidad"] = "Ya existe un cliente con este documento de identidad."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.nombre


class TipoPago(models.Model):
    nombre = models.CharField(
        max_length=50,
        validators=[MaxLengthValidator(50)],
    )

    class Meta:
        verbose_name = "tipo de pago"
        verbose_name_plural = "tipos de pago"
        ordering = ["nombre", "id"]
        indexes = [
            models.Index(fields=["nombre"], name="tipo_pago_nombre_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                Lower("nombre"),
                name="tipo_pago_nombre_unico_ci",
            ),
        ]

    def clean(self):
        super().clean()

        self.nombre = _strip_or_empty(self.nombre)

        errors = {}

        if not self.nombre:
            errors["nombre"] = "El nombre del tipo de pago es obligatorio."
        elif len(self.nombre) < 2:
            errors["nombre"] = "El nombre del tipo de pago debe tener al menos 2 caracteres."

        duplicado = TipoPago.objects.filter(nombre__iexact=self.nombre).exclude(pk=self.pk).exists()

        if self.nombre and duplicado:
            errors["nombre"] = "Ya existe un tipo de pago con este nombre."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.nombre


class Descuento(models.Model):
    nombre = models.CharField(
        max_length=100,
        validators=[MaxLengthValidator(100)],
    )
    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()

    class Meta:
        verbose_name = "descuento"
        verbose_name_plural = "descuentos"
        ordering = ["-fecha_inicio", "-id"]
        indexes = [
            models.Index(fields=["nombre"], name="descuento_nombre_idx"),
            models.Index(fields=["fecha_inicio"], name="descuento_inicio_idx"),
            models.Index(fields=["fecha_fin"], name="descuento_fin_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(porcentaje__gte=0) & Q(porcentaje__lte=100),
                name="descuento_porcentaje_rango_valido",
            ),
            models.CheckConstraint(
                condition=Q(fecha_fin__gt=models.F("fecha_inicio")),
                name="descuento_fecha_fin_posterior",
            ),
        ]

    def clean(self):
        super().clean()

        self.nombre = _strip_or_empty(self.nombre)

        errors = {}

        if not self.nombre:
            errors["nombre"] = "El nombre del descuento es obligatorio."
        elif len(self.nombre) < 3:
            errors["nombre"] = "El nombre del descuento debe tener al menos 3 caracteres."

        if self.porcentaje is None:
            errors["porcentaje"] = "El porcentaje del descuento es obligatorio."
        elif self.porcentaje < Decimal("0.00") or self.porcentaje > Decimal("100.00"):
            errors["porcentaje"] = "El porcentaje debe estar entre 0 y 100."

        if not self.fecha_inicio:
            errors["fecha_inicio"] = "La fecha de inicio es obligatoria."

        if not self.fecha_fin:
            errors["fecha_fin"] = "La fecha de fin es obligatoria."

        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            errors["fecha_fin"] = "La fecha de fin debe ser posterior a la fecha de inicio."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje}%)"


class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.RESTRICT,
        related_name="ventas",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        related_name="ventas",
    )
    descuento = models.ForeignKey(
        Descuento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas",
    )

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(fields=["fecha"], name="venta_fecha_idx"),
            models.Index(fields=["cliente"], name="venta_cliente_idx"),
            models.Index(fields=["usuario"], name="venta_usuario_idx"),
            models.Index(fields=["descuento"], name="venta_descuento_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="venta_total_no_negativo",
            ),
        ]

    def clean(self):
        super().clean()

        if self.total is not None and self.total < Decimal("0.00"):
            raise ValidationError({"total": "El total de la venta no puede ser negativo."})

    def __str__(self):
        cliente = self.cliente.nombre if self.cliente_id else "Sin cliente"
        return f"Venta #{self.id or 'Nueva'} - {cliente}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        related_name="detalles_venta",
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["venta"], name="detalle_venta_venta_idx"),
            models.Index(fields=["producto"], name="detalle_venta_producto_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad__gte=1),
                name="detalle_venta_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=Q(precio_unitario__gte=0),
                name="detalle_venta_precio_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="detalle_venta_subtotal_no_negativo",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.cantidad is None:
            errors["cantidad"] = "La cantidad vendida es obligatoria."
        elif self.cantidad < 1:
            errors["cantidad"] = "La cantidad vendida debe ser mayor a cero."

        if not self.producto_id:
            errors["producto"] = "Debe seleccionar un producto."

        if self.producto_id and self.cantidad:
            producto = Producto.objects.filter(pk=self.producto_id).only("stock_actual", "nombre").first()

            if producto and producto.stock_actual < self.cantidad:
                errors["cantidad"] = f"Stock insuficiente. Disponible: {producto.stock_actual}."

        if self.precio_unitario is None:
            errors["precio_unitario"] = "El precio unitario es obligatorio."
        elif self.precio_unitario < Decimal("0.00"):
            errors["precio_unitario"] = "El precio unitario no puede ser negativo."

        if self.subtotal is None:
            errors["subtotal"] = "El subtotal es obligatorio."
        elif self.subtotal < Decimal("0.00"):
            errors["subtotal"] = "El subtotal no puede ser negativo."

        if self.cantidad and self.precio_unitario is not None:
            subtotal_calculado = self.cantidad * self.precio_unitario
            if self.subtotal != subtotal_calculado:
                self.subtotal = subtotal_calculado

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        venta_id = self.venta_id or "Nueva"
        producto = self.producto.nombre if self.producto_id else "Sin producto"
        return f"Detalle Venta #{venta_id} - {producto}"


class Pago(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="pagos",
    )
    tipo_pago = models.ForeignKey(
        TipoPago,
        on_delete=models.RESTRICT,
        related_name="pagos",
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    fecha_pago = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        ordering = ["-fecha_pago", "-id"]
        indexes = [
            models.Index(fields=["venta"], name="pago_venta_idx"),
            models.Index(fields=["tipo_pago"], name="pago_tipo_pago_idx"),
            models.Index(fields=["fecha_pago"], name="pago_fecha_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gte=0),
                name="pago_monto_no_negativo",
            ),
        ]

    def clean(self):
        super().clean()

        if self.monto is not None and self.monto < Decimal("0.00"):
            raise ValidationError({"monto": "El monto del pago no puede ser negativo."})

    def __str__(self):
        venta_id = self.venta_id or "Nueva"
        return f"Pago #{self.id or 'Nuevo'} de Venta #{venta_id}"