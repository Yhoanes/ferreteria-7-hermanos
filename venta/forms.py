import json
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from producto.models import Producto
from .models import Cliente, Descuento, TipoPago


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


class ClienteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nombre", "documento_identidad", "telefono", "direccion"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "maxlength": "150",
                "placeholder": "Ej: Juan Pérez",
                "autocomplete": "name",
            }),
            "documento_identidad": forms.TextInput(attrs={
                "maxlength": "50",
                "placeholder": "Ej: 12345678",
                "autocomplete": "off",
            }),
            "telefono": forms.TextInput(attrs={
                "maxlength": "20",
                "placeholder": "Ej: 70000000",
                "autocomplete": "tel",
                "pattern": r"[0-9+\-\s]+",
            }),
            "direccion": forms.TextInput(attrs={
                "maxlength": "255",
                "placeholder": "Ej: Av. Principal #123",
                "autocomplete": "street-address",
            }),
        }
        error_messages = {
            "nombre": {
                "required": "El nombre del cliente es obligatorio.",
                "max_length": "El nombre no puede superar los 150 caracteres.",
            },
            "documento_identidad": {
                "required": "El documento de identidad es obligatorio.",
                "max_length": "El documento no puede superar los 50 caracteres.",
            },
            "telefono": {
                "max_length": "El teléfono no puede superar los 20 caracteres.",
            },
            "direccion": {
                "max_length": "La dirección no puede superar los 255 caracteres.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["nombre"].required = True
        self.fields["documento_identidad"].required = True
        self.fields["telefono"].required = False
        self.fields["direccion"].required = False

        self._apply_bootstrap()

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()

        if not nombre:
            raise ValidationError("El nombre del cliente es obligatorio.")

        if len(nombre) < 3:
            raise ValidationError("El nombre del cliente debe tener al menos 3 caracteres.")

        return nombre

    def clean_documento_identidad(self):
        documento = (self.cleaned_data.get("documento_identidad") or "").strip()

        if not documento:
            raise ValidationError("El documento de identidad es obligatorio.")

        if len(documento) < 3:
            raise ValidationError("El documento de identidad debe tener al menos 3 caracteres.")

        existe = Cliente.objects.filter(
            documento_identidad__iexact=documento
        ).exclude(pk=self.instance.pk).exists()

        if existe:
            raise ValidationError("Ya existe un cliente con este documento de identidad.")

        return documento

    def clean_telefono(self):
        telefono = (self.cleaned_data.get("telefono") or "").strip()

        if not telefono:
            return None

        telefono_limpio = telefono.replace("+", "").replace(" ", "").replace("-", "")

        if not telefono_limpio.isdigit():
            raise ValidationError("El teléfono solo debe contener números, espacios, + o guiones.")

        if len(telefono_limpio) < 7:
            raise ValidationError("El teléfono debe tener al menos 7 números.")

        return telefono

    def clean_direccion(self):
        direccion = (self.cleaned_data.get("direccion") or "").strip()

        if not direccion:
            return None

        if len(direccion) < 5:
            raise ValidationError("La dirección debe tener al menos 5 caracteres.")

        return direccion


class TipoPagoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TipoPago
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "maxlength": "50",
                "placeholder": "Ej: Efectivo, QR, Tarjeta, Transferencia",
                "autocomplete": "off",
            }),
        }
        error_messages = {
            "nombre": {
                "required": "El nombre del tipo de pago es obligatorio.",
                "max_length": "El nombre no puede superar los 50 caracteres.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["nombre"].required = True
        self._apply_bootstrap()

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()

        if not nombre:
            raise ValidationError("El nombre del tipo de pago es obligatorio.")

        if len(nombre) < 2:
            raise ValidationError("El nombre del tipo de pago debe tener al menos 2 caracteres.")

        existe = TipoPago.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists()

        if existe:
            raise ValidationError("Ya existe un tipo de pago con este nombre.")

        return nombre


class DescuentoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Descuento
        fields = ["nombre", "porcentaje", "fecha_inicio", "fecha_fin"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "maxlength": "100",
                "placeholder": "Ej: Promoción de temporada",
                "autocomplete": "off",
            }),
            "porcentaje": forms.NumberInput(attrs={
                "min": "0",
                "max": "100",
                "step": "0.01",
                "placeholder": "Ej: 10",
                "inputmode": "decimal",
            }),
            "fecha_inicio": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "fecha_fin": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
        }
        error_messages = {
            "nombre": {
                "required": "El nombre del descuento es obligatorio.",
                "max_length": "El nombre no puede superar los 100 caracteres.",
            },
            "porcentaje": {
                "required": "El porcentaje del descuento es obligatorio.",
                "invalid": "El porcentaje debe ser un número válido.",
            },
            "fecha_inicio": {
                "required": "La fecha de inicio es obligatoria.",
                "invalid": "La fecha de inicio no tiene un formato válido.",
            },
            "fecha_fin": {
                "required": "La fecha de fin es obligatoria.",
                "invalid": "La fecha de fin no tiene un formato válido.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["nombre"].required = True
        self.fields["porcentaje"].required = True
        self.fields["fecha_inicio"].required = True
        self.fields["fecha_fin"].required = True

        self.fields["fecha_inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["fecha_fin"].input_formats = ["%Y-%m-%dT%H:%M"]

        self._apply_bootstrap()

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()

        if not nombre:
            raise ValidationError("El nombre del descuento es obligatorio.")

        if len(nombre) < 3:
            raise ValidationError("El nombre del descuento debe tener al menos 3 caracteres.")

        return nombre

    def clean_porcentaje(self):
        porcentaje = self.cleaned_data.get("porcentaje")

        if porcentaje is None:
            raise ValidationError("El porcentaje del descuento es obligatorio.")

        try:
            porcentaje = Decimal(porcentaje)
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("El porcentaje debe ser un número válido.")

        if porcentaje < Decimal("0.00"):
            raise ValidationError("El porcentaje no puede ser negativo.")

        if porcentaje > Decimal("100.00"):
            raise ValidationError("El porcentaje no puede ser mayor a 100.")

        return porcentaje

    def clean(self):
        cleaned = super().clean()

        fecha_inicio = cleaned.get("fecha_inicio")
        fecha_fin = cleaned.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            self.add_error("fecha_fin", "La fecha de fin debe ser posterior a la fecha de inicio.")

        return cleaned


class VentaCheckoutForm(BootstrapFormMixin, forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        required=True,
        empty_label="Seleccione un cliente",
        error_messages={
            "required": "Debe seleccionar un cliente.",
            "invalid_choice": "El cliente seleccionado no es válido.",
        },
    )
    tipo_pago = forms.ModelChoiceField(
        queryset=TipoPago.objects.none(),
        required=True,
        empty_label="Seleccione un método de pago",
        error_messages={
            "required": "Debe seleccionar un método de pago.",
            "invalid_choice": "El método de pago seleccionado no es válido.",
        },
    )
    descuento = forms.ModelChoiceField(
        queryset=Descuento.objects.none(),
        required=False,
        empty_label="Sin descuento",
        error_messages={
            "invalid_choice": "El descuento seleccionado no es válido.",
        },
    )
    carrito_datos = forms.CharField(
        widget=forms.HiddenInput,
        required=True,
        error_messages={
            "required": "Debe agregar productos al carrito.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ahora = timezone.now()

        self.fields["cliente"].queryset = Cliente.objects.filter(activo=True).order_by("nombre")
        self.fields["tipo_pago"].queryset = TipoPago.objects.all().order_by("nombre")
        self.fields["descuento"].queryset = Descuento.objects.filter(
            fecha_inicio__lte=ahora,
            fecha_fin__gte=ahora,
        ).order_by("nombre")

        self.fields["cliente"].widget.attrs.update({
            "autocomplete": "off",
        })
        self.fields["tipo_pago"].widget.attrs.update({
            "autocomplete": "off",
        })
        self.fields["descuento"].widget.attrs.update({
            "autocomplete": "off",
        })

        self._apply_bootstrap()

    def clean_carrito_datos(self):
        raw_data = self.cleaned_data.get("carrito_datos")

        if not raw_data:
            raise ValidationError("Debe agregar al menos un producto a la venta.")

        try:
            carrito = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            raise ValidationError("El detalle de productos no tiene un formato válido.") from exc

        if not isinstance(carrito, list) or not carrito:
            raise ValidationError("Debe agregar al menos un producto a la venta.")

        productos_validados = []
        productos_acumulados = {}

        for item in carrito:
            if not isinstance(item, dict):
                raise ValidationError("El detalle de productos no tiene un formato válido.")

            try:
                producto_id = int(item.get("id_producto"))
                cantidad = int(item.get("cantidad"))
            except (TypeError, ValueError) as exc:
                raise ValidationError("Cada producto debe tener una cantidad numérica válida.") from exc

            if cantidad < 1:
                raise ValidationError("La cantidad de cada producto debe ser mayor a cero.")

            if producto_id in productos_acumulados:
                productos_acumulados[producto_id] += cantidad
            else:
                productos_acumulados[producto_id] = cantidad

        for producto_id, cantidad_total in productos_acumulados.items():
            try:
                producto = Producto.objects.get(id=producto_id, activo=True)
            except Producto.DoesNotExist as exc:
                raise ValidationError("Uno de los productos seleccionados ya no está disponible.") from exc

            if producto.stock_actual < cantidad_total:
                raise ValidationError(
                    f"No hay suficiente stock de {producto.nombre}. Disponible: {producto.stock_actual}."
                )

            productos_validados.append({
                "producto": producto,
                "cantidad": cantidad_total,
            })

        return productos_validados