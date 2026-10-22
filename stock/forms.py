from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError

from producto.models import Producto, Proveedor


MOTIVOS_SALIDA = [
    ("Dañado/Roto", "Producto dañado / roto"),
    ("Vencido", "Fecha de caducidad vencida"),
    ("Uso Interno", "Uso interno de la ferretería"),
    ("Pérdida/Robo", "Pérdida / inventario no coincide"),
    ("Ajuste/Corrección", "Ajuste o corrección por error de ingreso"),
]


class BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "form-control")
                widget.attrs.setdefault("rows", 2)
            else:
                widget.attrs.setdefault("class", "form-control")


class EntradaStockForm(BootstrapFormMixin, forms.Form):
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.none(),
        required=True,
        empty_label="Seleccione un proveedor",
        error_messages={
            "required": "Debe seleccionar un proveedor.",
            "invalid_choice": "El proveedor seleccionado no es válido.",
        },
    )
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.none(),
        required=True,
        empty_label="Seleccione un producto",
        error_messages={
            "required": "Debe seleccionar un producto.",
            "invalid_choice": "El producto seleccionado no es válido.",
        },
    )
    cantidad = forms.IntegerField(
        min_value=1,
        required=True,
        error_messages={
            "required": "La cantidad es obligatoria.",
            "min_value": "La cantidad debe ser mayor a cero.",
            "invalid": "La cantidad debe ser un número válido.",
        },
    )
    costo = forms.DecimalField(
        min_value=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        required=True,
        error_messages={
            "required": "El costo unitario es obligatorio.",
            "min_value": "El costo unitario no puede ser negativo.",
            "invalid": "El costo unitario debe ser un número válido.",
            "max_digits": "El costo unitario tiene demasiados dígitos.",
            "max_decimal_places": "El costo unitario solo puede tener dos decimales.",
        },
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["proveedor"].queryset = Proveedor.objects.all().order_by("nombre_empresa")
        self.fields["producto"].queryset = Producto.objects.filter(activo=True).order_by("nombre")

        self.fields["proveedor"].widget.attrs.update({
            "autocomplete": "off",
        })
        self.fields["producto"].widget.attrs.update({
            "autocomplete": "off",
        })
        self.fields["cantidad"].widget.attrs.update({
            "min": "1",
            "inputmode": "numeric",
            "placeholder": "Ej: 10",
        })
        self.fields["costo"].widget.attrs.update({
            "min": "0",
            "step": "0.01",
            "inputmode": "decimal",
            "placeholder": "0.00",
        })
        self.fields["observacion"].widget.attrs.update({
            "placeholder": "Observación opcional sobre la entrada de stock...",
            "maxlength": "500",
        })

        self._apply_bootstrap()

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")

        if cantidad is None:
            raise ValidationError("La cantidad es obligatoria.")

        if cantidad < 1:
            raise ValidationError("La cantidad debe ser mayor a cero.")

        return cantidad

    def clean_costo(self):
        costo = self.cleaned_data.get("costo")

        if costo is None:
            raise ValidationError("El costo unitario es obligatorio.")

        try:
            costo = Decimal(costo)
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("El costo unitario debe ser un número válido.")

        if costo < Decimal("0.00"):
            raise ValidationError("El costo unitario no puede ser negativo.")

        return costo

    def clean_observacion(self):
        observacion = (self.cleaned_data.get("observacion") or "").strip()

        if observacion and len(observacion) < 3:
            raise ValidationError("La observación debe tener al menos 3 caracteres.")

        if len(observacion) > 500:
            raise ValidationError("La observación no puede superar los 500 caracteres.")

        return observacion


class SalidaStockForm(BootstrapFormMixin, forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.none(),
        required=True,
        empty_label="Seleccione un producto",
        error_messages={
            "required": "Debe seleccionar un producto.",
            "invalid_choice": "El producto seleccionado no es válido.",
        },
    )
    cantidad = forms.IntegerField(
        min_value=1,
        required=True,
        error_messages={
            "required": "La cantidad es obligatoria.",
            "min_value": "La cantidad debe ser mayor a cero.",
            "invalid": "La cantidad debe ser un número válido.",
        },
    )
    motivo = forms.ChoiceField(
        choices=[("", "Seleccione el motivo")] + MOTIVOS_SALIDA,
        required=True,
        error_messages={
            "required": "El motivo de la salida es obligatorio.",
            "invalid_choice": "El motivo seleccionado no es válido.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["producto"].queryset = Producto.objects.filter(
            stock_actual__gt=0,
            activo=True,
        ).order_by("nombre")

        self.fields["producto"].widget.attrs.update({
            "autocomplete": "off",
        })
        self.fields["cantidad"].widget.attrs.update({
            "min": "1",
            "inputmode": "numeric",
            "placeholder": "Ej: 5",
        })
        self.fields["motivo"].widget.attrs.update({
            "autocomplete": "off",
        })

        self._apply_bootstrap()

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")

        if cantidad is None:
            raise ValidationError("La cantidad es obligatoria.")

        if cantidad < 1:
            raise ValidationError("La cantidad debe ser mayor a cero.")

        return cantidad

    def clean_motivo(self):
        motivo = (self.cleaned_data.get("motivo") or "").strip()

        if not motivo:
            raise ValidationError("El motivo de la salida es obligatorio.")

        motivos_validos = [valor for valor, _ in MOTIVOS_SALIDA]

        if motivo not in motivos_validos:
            raise ValidationError("El motivo seleccionado no es válido.")

        return motivo

    def clean(self):
        cleaned = super().clean()

        producto = cleaned.get("producto")
        cantidad = cleaned.get("cantidad")

        if producto and cantidad:
            producto_actualizado = Producto.objects.filter(pk=producto.pk).only("stock_actual").first()

            if not producto_actualizado:
                self.add_error("producto", "El producto seleccionado no existe.")
            elif cantidad > producto_actualizado.stock_actual:
                self.add_error(
                    "cantidad",
                    f"No existe stock suficiente. Disponible: {producto_actualizado.stock_actual}.",
                )

        return cleaned