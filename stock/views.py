from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.shortcuts import redirect, render

from administracion.decorators import requiere_permiso
from administracion.models import Usuario
from producto.models import Producto, Proveedor
from .forms import EntradaStockForm, SalidaStockForm
from .models import DetalleEntrada, DetalleSalida, EntradaStock, SalidaStock


def _usuario_actual(request):
    if not request.user.is_authenticated:
        return None

    email = (request.user.email or "").strip()

    if not email:
        return None

    return Usuario.objects.filter(correo__iexact=email).first()


def _entrada_context(form):
    return {
        "form": form,
        "productos": Producto.objects.filter(activo=True).order_by("nombre"),
        "proveedores": Proveedor.objects.all().order_by("nombre_empresa"),
    }


def _salida_context(form):
    return {
        "form": form,
        "productos": Producto.objects.filter(stock_actual__gt=0, activo=True).order_by("nombre"),
    }


@requiere_permiso("view_entradastock")
def lista_entradas(request):
    entradas = (
        EntradaStock.objects
        .select_related("proveedor", "usuario")
        .prefetch_related("detalles__producto", "detalles__producto__marca")
        .order_by("-fecha", "-id")
    )

    return render(request, "entradas_lista.html", {"entradas": entradas})


@requiere_permiso("add_entradastock")
def registrar_entrada(request):
    form = EntradaStockForm(request.POST or None)

    if request.method == "POST":
        usuario_ferreteria = _usuario_actual(request)

        if not usuario_ferreteria:
            messages.error(request, "No se puede registrar la entrada porque tu cuenta no está vinculada al sistema interno.")
            return render(request, "registrar_stock.html", _entrada_context(form))

        if form.is_valid():
            proveedor = form.cleaned_data["proveedor"]
            producto_form = form.cleaned_data["producto"]
            cantidad = form.cleaned_data["cantidad"]
            costo = form.cleaned_data["costo"]
            observacion = form.cleaned_data.get("observacion") or "Ingreso de mercadería por sistema"

            try:
                with transaction.atomic():
                    producto = Producto.objects.select_for_update().get(pk=producto_form.pk)

                    if not producto.activo:
                        form.add_error("producto", "No se puede registrar stock para un producto inactivo.")
                        return render(request, "registrar_stock.html", _entrada_context(form))

                    nueva_entrada = EntradaStock(
                        proveedor=proveedor,
                        usuario=usuario_ferreteria,
                        observacion=observacion,
                    )
                    nueva_entrada.full_clean()
                    nueva_entrada.save()

                    detalle = DetalleEntrada(
                        entrada=nueva_entrada,
                        producto=producto,
                        cantidad=cantidad,
                        costo_unitario=costo,
                    )
                    detalle.full_clean()
                    detalle.save()

                    Producto.objects.filter(pk=producto.pk).update(
                        stock_actual=F("stock_actual") + cantidad
                    )

                messages.success(request, f"Entrada registrada correctamente. Se agregaron {cantidad} unidades a {producto_form.nombre}.")
                return redirect("lista_entradas")

            except Producto.DoesNotExist:
                form.add_error("producto", "El producto seleccionado ya no existe.")
            except ValidationError as error:
                if hasattr(error, "message_dict"):
                    for campo, errores in error.message_dict.items():
                        if campo in form.fields:
                            for mensaje in errores:
                                form.add_error(campo, mensaje)
                        else:
                            messages.error(request, " ".join(errores))
                else:
                    messages.error(request, "No se pudo registrar la entrada de stock por una validación del sistema.")
            except Exception as error:
                messages.error(request, f"No se pudo registrar la entrada de stock. Error interno: {error}")

    return render(request, "registrar_stock.html", _entrada_context(form))


@requiere_permiso("view_salidastock")
def lista_salidas(request):
    salidas = (
        SalidaStock.objects
        .select_related("usuario")
        .prefetch_related("detalles__producto", "detalles__producto__marca")
        .order_by("-fecha", "-id")
    )

    return render(request, "salidas_lista.html", {"salidas": salidas})


@requiere_permiso("add_salidastock")
def registrar_salida(request):
    form = SalidaStockForm(request.POST or None)

    if request.method == "POST":
        usuario_ferreteria = _usuario_actual(request)

        if not usuario_ferreteria:
            messages.error(request, "No se puede registrar la salida porque tu cuenta no está vinculada al sistema interno.")
            return render(request, "salidas_registrar.html", _salida_context(form))

        if form.is_valid():
            producto_form = form.cleaned_data["producto"]
            cantidad = form.cleaned_data["cantidad"]
            motivo = form.cleaned_data["motivo"]

            try:
                with transaction.atomic():
                    producto = Producto.objects.select_for_update().get(pk=producto_form.pk)

                    if not producto.activo:
                        form.add_error("producto", "No se puede registrar salida para un producto inactivo.")
                        return render(request, "salidas_registrar.html", _salida_context(form))

                    if producto.stock_actual < cantidad:
                        form.add_error("cantidad", f"No existe stock suficiente. Disponible: {producto.stock_actual}.")
                        return render(request, "salidas_registrar.html", _salida_context(form))

                    nueva_salida = SalidaStock(
                        motivo=motivo,
                        usuario=usuario_ferreteria,
                    )
                    nueva_salida.full_clean()
                    nueva_salida.save()

                    detalle = DetalleSalida(
                        salida=nueva_salida,
                        producto=producto,
                        cantidad=cantidad,
                    )
                    detalle.full_clean()
                    detalle.save()

                    Producto.objects.filter(pk=producto.pk).update(
                        stock_actual=F("stock_actual") - cantidad
                    )

                messages.success(request, f"Salida registrada correctamente. Se descontaron {cantidad} unidades de {producto_form.nombre}.")
                return redirect("lista_salidas")

            except Producto.DoesNotExist:
                form.add_error("producto", "El producto seleccionado ya no existe.")
            except ValidationError as error:
                if hasattr(error, "message_dict"):
                    for campo, errores in error.message_dict.items():
                        if campo in form.fields:
                            for mensaje in errores:
                                form.add_error(campo, mensaje)
                        else:
                            messages.error(request, " ".join(errores))
                else:
                    messages.error(request, "No se pudo registrar la salida de stock por una validación del sistema.")
            except Exception as error:
                messages.error(request, f"No se pudo registrar la salida de stock. Error interno: {error}")

    return render(request, "salidas_registrar.html", _salida_context(form))