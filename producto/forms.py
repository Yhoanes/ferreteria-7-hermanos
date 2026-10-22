from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError

from .models import Categoria, Marca, Producto, Proveedor


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


class CategoriaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "maxlength": 100,
                "required": True,
                "autocomplete": "off",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "maxlength": 500,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()

        if not nombre:
            raise ValidationError("El nombre de la categoría es obligatorio.")

        if len(nombre) < 3:
            raise ValidationError("El nombre de la categoría debe tener al menos 3 caracteres.")

        existe = Categoria.objects.filter(nombre__iexact=nombre)

        if self.instance and self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)

        if existe.exists():
            raise ValidationError("Ya existe una categoría con este nombre.")

        return nombre

    def clean_descripcion(self):
        return (self.cleaned_data.get("descripcion") or "").strip()


class MarcaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Marca
        fields = ["nombre", "descripcion"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "maxlength": 100,
                "required": True,
                "autocomplete": "off",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "maxlength": 500,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()

        if not nombre:
            raise ValidationError("El nombre de la marca es obligatorio.")

        if len(nombre) < 2:
            raise ValidationError("El nombre de la marca debe tener al menos 2 caracteres.")

        existe = Marca.objects.filter(nombre__iexact=nombre)

        if self.instance and self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)

        if existe.exists():
            raise ValidationError("Ya existe una marca con este nombre.")

        return nombre

    def clean_descripcion(self):
        return (self.cleaned_data.get("descripcion") or "").strip()


class ProveedorForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre_empresa", "contacto", "telefono", "direccion"]
        widgets = {
            "nombre_empresa": forms.TextInput(attrs={
                "maxlength": 150,
                "required": True,
                "autocomplete": "organization",
            }),
            "contacto": forms.TextInput(attrs={
                "maxlength": 100,
                "required": True,
                "autocomplete": "name",
            }),
            "telefono": forms.TextInput(attrs={
                "maxlength": 20,
                "required": True,
                "pattern": r"[0-9+\-\s]+",
                "inputmode": "tel",
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

    def clean_nombre_empresa(self):
        nombre_empresa = self.cleaned_data.get("nombre_empresa", "").strip()

        if not nombre_empresa:
            raise ValidationError("El nombre de la empresa es obligatorio.")

        if len(nombre_empresa) < 3:
            raise ValidationError("El nombre de la empresa debe tener al menos 3 caracteres.")

        return nombre_empresa

    def clean_contacto(self):
        contacto = self.cleaned_data.get("contacto", "").strip()

        if not contacto:
            raise ValidationError("El contacto del proveedor es obligatorio.")

        if len(contacto) < 3:
            raise ValidationError("El contacto debe tener al menos 3 caracteres.")

        return contacto

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono", "").strip()

        if not telefono:
            raise ValidationError("El teléfono del proveedor es obligatorio.")

        telefono_limpio = telefono.replace("+", "").replace(" ", "").replace("-", "")

        if not telefono_limpio.isdigit():
            raise ValidationError("El teléfono solo debe contener números, espacios, + o guiones.")

        if len(telefono_limpio) < 7:
            raise ValidationError("El teléfono debe tener al menos 7 dígitos.")

        return telefono

    def clean_direccion(self):
        direccion = self.cleaned_data.get("direccion", "").strip()

        if not direccion:
            raise ValidationError("La dirección del proveedor es obligatoria.")

        if len(direccion) < 5:
            raise ValidationError("La dirección debe tener al menos 5 caracteres.")

        return direccion


class ProductoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "codigo",
            "nombre",
            "descripcion",
            "precio_compra",
            "precio_venta",
            "stock_minimo",
            "categoria",
            "marca",
            "proveedor",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={
                "maxlength": 50,
                "required": True,
                "autocomplete": "off",
            }),
            "nombre": forms.TextInput(attrs={
                "maxlength": 150,
                "required": True,
                "autocomplete": "off",
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "maxlength": 500,
            }),
            "precio_compra": forms.NumberInput(attrs={
                "min": 0,
                "step": "0.01",
                "required": True,
                "inputmode": "decimal",
            }),
            "precio_venta": forms.NumberInput(attrs={
                "min": 0,
                "step": "0.01",
                "required": True,
                "inputmode": "decimal",
            }),
            "stock_minimo": forms.NumberInput(attrs={
                "min": 0,
                "step": "1",
                "required": True,
                "inputmode": "numeric",
            }),
        }

    def __init__(self, *args, readonly_codigo=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["categoria"].queryset = Categoria.objects.all().order_by("nombre")
        self.fields["marca"].queryset = Marca.objects.all().order_by("nombre")
        self.fields["proveedor"].queryset = Proveedor.objects.all().order_by("nombre_empresa")

        self.fields["categoria"].empty_label = "Seleccione una categoría"
        self.fields["marca"].empty_label = "Sin marca"
        self.fields["proveedor"].empty_label = "Seleccione un proveedor"

        self.fields["marca"].required = False

        self._apply_bootstrap()

        if readonly_codigo:
            self.fields["codigo"].widget.attrs["readonly"] = True
            self.fields["codigo"].widget.attrs["class"] = "form-control bg-light"

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo", "").strip().upper()

        if not codigo:
            raise ValidationError("El código del producto es obligatorio.")

        if len(codigo) < 2:
            raise ValidationError("El código del producto debe tener al menos 2 caracteres.")

        existe = Producto.objects.filter(codigo__iexact=codigo)

        if self.instance and self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)

        if existe.exists():
            raise ValidationError("Ya existe un producto con este código.")

        return codigo

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()

        if not nombre:
            raise ValidationError("El nombre del producto es obligatorio.")

        if len(nombre) < 3:
            raise ValidationError("El nombre del producto debe tener al menos 3 caracteres.")

        return nombre

    def clean_descripcion(self):
        return (self.cleaned_data.get("descripcion") or "").strip()

    def clean_precio_compra(self):
        precio = self.cleaned_data.get("precio_compra")

        if precio is None:
            raise ValidationError("El precio de compra es obligatorio.")

        try:
            precio = Decimal(precio)
        except (InvalidOperation, TypeError):
            raise ValidationError("El precio de compra no es válido.")

        if precio < Decimal("0.00"):
            raise ValidationError("El precio de compra no puede ser negativo.")

        return precio

    def clean_precio_venta(self):
        precio = self.cleaned_data.get("precio_venta")

        if precio is None:
            raise ValidationError("El precio de venta es obligatorio.")

        try:
            precio = Decimal(precio)
        except (InvalidOperation, TypeError):
            raise ValidationError("El precio de venta no es válido.")

        if precio < Decimal("0.00"):
            raise ValidationError("El precio de venta no puede ser negativo.")

        return precio

    def clean_stock_minimo(self):
        stock_minimo = self.cleaned_data.get("stock_minimo")

        if stock_minimo is None:
            raise ValidationError("El stock mínimo es obligatorio.")

        if stock_minimo < 0:
            raise ValidationError("El stock mínimo no puede ser negativo.")

        return stock_minimo

    def clean(self):
        cleaned_data = super().clean()

        precio_compra = cleaned_data.get("precio_compra")
        precio_venta = cleaned_data.get("precio_venta")
        categoria = cleaned_data.get("categoria")
        proveedor = cleaned_data.get("proveedor")

        if precio_compra is not None and precio_venta is not None:
            if precio_venta < precio_compra:
                self.add_error("precio_venta", "El precio de venta no puede ser menor al precio de compra.")

        if categoria is None:
            self.add_error("categoria", "La categoría del producto es obligatoria.")

        if proveedor is None:
            self.add_error("proveedor", "El proveedor del producto es obligatorio.")

        return cleaned_data