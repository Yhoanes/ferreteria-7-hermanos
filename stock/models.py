from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from administracion.models import Usuario
from producto.models import Producto, Proveedor


def _strip_or_empty(value):
    return (value or "").strip()


class EntradaStock(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.TextField(blank=True, null=True)

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.RESTRICT,
        related_name="entradas_stock",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        related_name="entradas_stock",
    )

    class Meta:
        verbose_name = "entrada de stock"
        verbose_name_plural = "entradas de stock"
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(fields=["fecha"], name="entrada_fecha_idx"),
            models.Index(fields=["proveedor"], name="entrada_proveedor_idx"),
            models.Index(fields=["usuario"], name="entrada_usuario_idx"),
        ]

    def clean(self):
        super().clean()
        self.observacion = _strip_or_empty(self.observacion)

        if self.observacion and len(self.observacion) < 3:
            raise ValidationError({"observacion": "La observación debe tener al menos 3 caracteres."})

    def __str__(self):
        fecha = self.fecha.date() if self.fecha else "sin fecha"
        return f"Entrada de Stock #{self.id or 'Nueva'} - {fecha}"


class DetalleEntrada(models.Model):
    entrada = models.ForeignKey(
        EntradaStock,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        related_name="detalles_entrada",
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "detalle de entrada"
        verbose_name_plural = "detalles de entrada"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["entrada"], name="detalle_ent_entrada_idx"),
            models.Index(fields=["producto"], name="detalle_ent_producto_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad__gte=1),
                name="detalle_entrada_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=Q(costo_unitario__gte=0),
                name="detalle_entrada_costo_no_negativo",
            ),
        ]

    @property
    def subtotal(self):
        if self.cantidad is None or self.costo_unitario is None:
            return Decimal("0.00")
        return self.cantidad * self.costo_unitario

    def clean(self):
        super().clean()

        errors = {}

        if self.cantidad is None:
            errors["cantidad"] = "La cantidad de entrada es obligatoria."
        elif self.cantidad < 1:
            errors["cantidad"] = "La cantidad de entrada debe ser mayor a cero."

        if self.costo_unitario is None:
            errors["costo_unitario"] = "El costo unitario es obligatorio."
        elif self.costo_unitario < 0:
            errors["costo_unitario"] = "El costo unitario no puede ser negativo."

        if not self.producto_id:
            errors["producto"] = "Debe seleccionar un producto."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        entrada_id = self.entrada_id or "Nueva"
        producto = self.producto.nombre if self.producto_id else "Sin producto"
        return f"Detalle Entrada #{entrada_id} - {producto}"


class SalidaStock(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=255)

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        related_name="salidas_stock",
    )

    class Meta:
        verbose_name = "salida de stock"
        verbose_name_plural = "salidas de stock"
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(fields=["fecha"], name="salida_fecha_idx"),
            models.Index(fields=["usuario"], name="salida_usuario_idx"),
        ]

    def clean(self):
        super().clean()
        self.motivo = _strip_or_empty(self.motivo)

        if not self.motivo:
            raise ValidationError({"motivo": "El motivo de la salida es obligatorio."})

        if len(self.motivo) < 3:
            raise ValidationError({"motivo": "El motivo debe tener al menos 3 caracteres."})

    def __str__(self):
        fecha = self.fecha.date() if self.fecha else "sin fecha"
        return f"Salida de Stock #{self.id or 'Nueva'} - {fecha}"


class DetalleSalida(models.Model):
    salida = models.ForeignKey(
        SalidaStock,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        related_name="detalles_salida",
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = "detalle de salida"
        verbose_name_plural = "detalles de salida"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["salida"], name="detalle_sal_salida_idx"),
            models.Index(fields=["producto"], name="detalle_sal_producto_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad__gte=1),
                name="detalle_salida_cantidad_positiva",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.cantidad is None:
            errors["cantidad"] = "La cantidad de salida es obligatoria."
        elif self.cantidad < 1:
            errors["cantidad"] = "La cantidad de salida debe ser mayor a cero."

        if not self.producto_id:
            errors["producto"] = "Debe seleccionar un producto."

        if self.producto_id and self.cantidad:
            producto = Producto.objects.filter(pk=self.producto_id).only("stock_actual", "nombre").first()

            if producto and producto.stock_actual < self.cantidad:
                errors["cantidad"] = f"No existe stock suficiente. Disponible: {producto.stock_actual}."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        salida_id = self.salida_id or "Nueva"
        producto = self.producto.nombre if self.producto_id else "Sin producto"
        return f"Detalle Salida #{salida_id} - {producto}"