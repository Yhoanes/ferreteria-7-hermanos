from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, ProtectedError, RestrictedError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa

from administracion.decorators import requiere_permiso
from administracion.models import EmpresaConfig, Usuario
from producto.models import Producto
from .forms import ClienteForm, DescuentoForm, TipoPagoForm, VentaCheckoutForm
from .models import Cliente, Descuento, DetalleVenta, Pago, TipoPago, Venta

def _money(valor):
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _usuario_actual(request):
    if not request.user.is_authenticated:
        return None

    email = (request.user.email or "").strip()

    if not email:
        return None

    return Usuario.objects.filter(correo__iexact=email).first()


def _venta_context(form=None):
    ahora = timezone.now()

    return {
        "form": form or VentaCheckoutForm(),
        "productos": Producto.objects.filter(
            stock_actual__gt=0,
            activo=True,
        )
        .select_related("categoria", "marca")
        .order_by("nombre"),
        "clientes": Cliente.objects.filter(activo=True).order_by("nombre"),
        "tipos_pago": TipoPago.objects.all().order_by("nombre"),
        "descuentos": Descuento.objects.filter(
            fecha_inicio__lte=ahora,
            fecha_fin__gte=ahora,
        ).order_by("nombre"),
    }


def _validation_to_form_or_messages(request, form, error):
    if hasattr(error, "message_dict"):
        for campo, errores in error.message_dict.items():
            if campo in form.fields:
                for mensaje in errores:
                    form.add_error(campo, mensaje)
            else:
                for mensaje in errores:
                    messages.error(request, mensaje)
    else:
        messages.error(request, "No se pudo completar la operación por una validación del sistema.")


@requiere_permiso("add_venta")
def realizar_venta(request):
    if request.method == "POST":
        form = VentaCheckoutForm(request.POST)

        if not form.is_valid():
            return render(request, "nueva_venta.html", _venta_context(form=form))

        vendedor = _usuario_actual(request)

        if not vendedor:
            messages.error(
                request,
                "No se puede registrar la venta porque tu cuenta no está vinculada al sistema interno.",
            )
            return render(request, "nueva_venta.html", _venta_context(form=form))

        cliente = form.cleaned_data["cliente"]
        tipo_pago = form.cleaned_data["tipo_pago"]
        descuento = form.cleaned_data.get("descuento")
        carrito = form.cleaned_data["carrito_datos"]

        try:
            with transaction.atomic():
                productos_bloqueados = {}
                subtotal_bruto = Decimal("0.00")

                for item in carrito:
                    producto_form = item["producto"]
                    cantidad = item["cantidad"]

                    producto = Producto.objects.select_for_update().get(pk=producto_form.pk)

                    if not producto.activo:
                        form.add_error("carrito_datos", f"El producto {producto.nombre} está inactivo.")
                        return render(request, "nueva_venta.html", _venta_context(form=form))

                    if producto.stock_actual < cantidad:
                        form.add_error(
                            "carrito_datos",
                            f"No hay suficiente stock de {producto.nombre}. Disponible: {producto.stock_actual}.",
                        )
                        return render(request, "nueva_venta.html", _venta_context(form=form))

                    productos_bloqueados[producto.pk] = {
                        "producto": producto,
                        "cantidad": cantidad,
                    }

                    subtotal_bruto += _money(producto.precio_venta * cantidad)

                total_final = subtotal_bruto

                if descuento:
                    descuento_monto = _money(subtotal_bruto * (descuento.porcentaje / Decimal("100")))
                    total_final = subtotal_bruto - descuento_monto

                if total_final < Decimal("0.00"):
                    total_final = Decimal("0.00")

                total_final = _money(total_final)

                nueva_venta = Venta(
                    cliente=cliente,
                    usuario=vendedor,
                    descuento=descuento,
                    total=total_final,
                )
                nueva_venta.full_clean()
                nueva_venta.save()

                for item in productos_bloqueados.values():
                    producto = item["producto"]
                    cantidad = item["cantidad"]
                    subtotal_item = _money(producto.precio_venta * cantidad)

                    detalle = DetalleVenta(
                        venta=nueva_venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=producto.precio_venta,
                        subtotal=subtotal_item,
                    )
                    detalle.full_clean()
                    detalle.save()

                    Producto.objects.filter(pk=producto.pk).update(
                        stock_actual=F("stock_actual") - cantidad
                    )

                pago = Pago(
                    venta=nueva_venta,
                    tipo_pago=tipo_pago,
                    monto=total_final,
                )
                pago.full_clean()
                pago.save()

            messages.success(
                request,
                f"Venta registrada correctamente. Total cobrado: Bs. {total_final:.2f}.",
            )
            return redirect("historial_ventas")

        except Producto.DoesNotExist:
            form.add_error("carrito_datos", "Uno de los productos seleccionados ya no existe.")
        except ValidationError as error:
            _validation_to_form_or_messages(request, form, error)
        except Exception as error:
            messages.error(request, f"No se pudo registrar la venta. Error interno: {error}")

        return render(request, "nueva_venta.html", _venta_context(form=form))

    return render(request, "nueva_venta.html", _venta_context())


@requiere_permiso("view_venta")
def historial_ventas(request):
    ventas = (
        Venta.objects.select_related("cliente", "usuario", "descuento")
        .prefetch_related("detalles__producto", "pagos__tipo_pago")
        .order_by("-fecha", "-id")
    )

    return render(request, "historial_ventas.html", {"ventas": ventas})


@requiere_permiso("view_venta")
def detalle_venta(request, venta_id):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente", "usuario", "descuento")
        .prefetch_related(
            "detalles__producto",
            "detalles__producto__marca",
            "pagos__tipo_pago",
        ),
        id=venta_id,
    )

    detalles = venta.detalles.all()
    pago = venta.pagos.select_related("tipo_pago").first()
    subtotal_bruto = sum(item.subtotal for item in detalles)

    return render(
        request,
        "detalle_venta.html",
        {
            "venta": venta,
            "detalles": detalles,
            "pago": pago,
            "subtotal_bruto": subtotal_bruto,
        },
    )


@requiere_permiso("view_cliente")
def lista_clientes(request):
    clientes = Cliente.objects.all().order_by("nombre", "id")
    return render(request, "lista_clientes.html", {"clientes": clientes})


@requiere_permiso("add_cliente")
def nuevo_cliente(request):
    form = ClienteForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    cliente = form.save(commit=False)
                    cliente.full_clean()
                    cliente.save()

                messages.success(
                    request,
                    f"El cliente '{cliente.nombre}' fue registrado correctamente.",
                )
                return redirect("lista_clientes")

            except ValidationError as error:
                _validation_to_form_or_messages(request, form, error)

    return render(request, "nuevo_cliente.html", {"form": form})


@requiere_permiso("change_cliente")
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    form = ClienteForm(request.POST or None, instance=cliente)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    cliente = form.save(commit=False)
                    cliente.full_clean()
                    cliente.save()

                messages.success(
                    request,
                    f"Los datos del cliente '{cliente.nombre}' se actualizaron correctamente.",
                )
                return redirect("lista_clientes")

            except ValidationError as error:
                _validation_to_form_or_messages(request, form, error)

    return render(request, "editar_cliente.html", {"cliente": cliente, "form": form})


@requiere_permiso("delete_cliente")
def estado_cliente(request, cliente_id):
    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_clientes")

    cliente = get_object_or_404(Cliente, id=cliente_id)

    try:
        with transaction.atomic():
            cliente.activo = not cliente.activo
            cliente.full_clean()
            cliente.save(update_fields=["activo"])

        if cliente.activo:
            messages.success(request, f"El cliente '{cliente.nombre}' ha sido reactivado.")
        else:
            messages.warning(request, f"El cliente '{cliente.nombre}' ha sido dado de baja.")

    except ValidationError:
        messages.error(request, "No se pudo cambiar el estado del cliente.")

    return redirect("lista_clientes")


@requiere_permiso("add_cliente")
def crear_cliente_ajax(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "error": "Método no permitido.",
            },
            status=405,
        )

    form = ClienteForm(request.POST)

    if form.is_valid():
        try:
            with transaction.atomic():
                cliente = form.save(commit=False)
                cliente.full_clean()
                cliente.save()

            return JsonResponse(
                {
                    "success": True,
                    "id": cliente.id,
                    "nombre": cliente.nombre,
                }
            )

        except ValidationError as error:
            errores = []

            if hasattr(error, "message_dict"):
                for field_errors in error.message_dict.values():
                    errores.extend(field_errors)
            else:
                errores.append("No se pudo crear el cliente por una validación del sistema.")

            return JsonResponse(
                {
                    "success": False,
                    "error": " ".join(errores),
                },
                status=400,
            )

    errores = []

    for field_errors in form.errors.values():
        errores.extend(field_errors)

    return JsonResponse(
        {
            "success": False,
            "error": " ".join(errores),
        },
        status=400,
    )


@requiere_permiso("view_tipopago")
def lista_tipos_pago(request):
    tipos = TipoPago.objects.all().order_by("nombre", "id")
    return render(request, "lista_tipos_pago.html", {"tipos": tipos})


@requiere_permiso("add_tipopago")
def nuevo_tipo_pago(request):
    form = TipoPagoForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    tipo = form.save(commit=False)
                    tipo.full_clean()
                    tipo.save()

                messages.success(request, f"Tipo de pago '{tipo.nombre}' registrado correctamente.")
                return redirect("lista_tipos_pago")

            except ValidationError as error:
                _validation_to_form_or_messages(request, form, error)

    return render(request, "nuevo_tipo_pago.html", {"form": form})


@requiere_permiso("change_tipopago")
def editar_tipo_pago(request, tipo_id):
    tipo = get_object_or_404(TipoPago, id=tipo_id)
    form = TipoPagoForm(request.POST or None, instance=tipo)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    tipo = form.save(commit=False)
                    tipo.full_clean()
                    tipo.save()

                messages.success(request, f"Tipo de pago actualizado a '{tipo.nombre}'.")
                return redirect("lista_tipos_pago")

            except ValidationError as error:
                _validation_to_form_or_messages(request, form, error)

    return render(request, "editar_tipo_pago.html", {"tipo": tipo, "form": form})


@requiere_permiso("delete_tipopago")
def eliminar_tipo_pago(request, tipo_id):
    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_tipos_pago")

    tipo = get_object_or_404(TipoPago, id=tipo_id)
    nombre = tipo.nombre

    try:
        with transaction.atomic():
            tipo.delete()

        messages.success(request, f"Tipo de pago '{nombre}' eliminado correctamente.")

    except (ProtectedError, RestrictedError):
        messages.error(
            request,
            f"No puedes eliminar el método '{nombre}' porque ya existen ventas registradas.",
        )

    return redirect("lista_tipos_pago")


@requiere_permiso("view_descuento")
def lista_descuentos(request):
    descuentos = Descuento.objects.all().order_by("-fecha_inicio", "-id")
    return render(request, "lista_descuentos.html", {"descuentos": descuentos})


@requiere_permiso("add_descuento")
def nuevo_descuento(request):
    form = DescuentoForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    descuento = form.save(commit=False)
                    descuento.full_clean()
                    descuento.save()

                messages.success(
                    request,
                    f"Descuento '{descuento.nombre}' programado correctamente.",
                )
                return redirect("lista_descuentos")

            except ValidationError as error:
                _validation_to_form_or_messages(request, form, error)

    return render(request, "nuevo_descuento.html", {"form": form})


@requiere_permiso("change_descuento")
def editar_descuento(request, descuento_id):
    descuento = get_object_or_404(Descuento, id=descuento_id)
    form = DescuentoForm(request.POST or None, instance=descuento)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    descuento = form.save(commit=False)
                    descuento.full_clean()
                    descuento.save()

                messages.success(
                    request,
                    f"Descuento '{descuento.nombre}' actualizado correctamente.",
                )
                return redirect("lista_descuentos")

            except ValidationError as error:
                _validation_to_form_or_messages(request, form, error)

    return render(
        request,
        "editar_descuento.html",
        {
            "descuento": descuento,
            "form": form,
        },
    )


@requiere_permiso("delete_descuento")
def eliminar_descuento(request, descuento_id):
    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_descuentos")

    descuento = get_object_or_404(Descuento, id=descuento_id)
    nombre = descuento.nombre

    try:
        with transaction.atomic():
            descuento.delete()

        messages.success(request, f"Descuento '{nombre}' eliminado del sistema.")

    except (ProtectedError, RestrictedError):
        messages.error(
            request,
            f"No puedes eliminar el descuento '{nombre}' porque ya existen ventas registradas.",
        )

    return redirect("lista_descuentos")


@requiere_permiso("view_venta")
def generar_recibo_pdf(request, venta_id):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente", "usuario", "descuento")
        .prefetch_related(
            "detalles__producto",
            "detalles__producto__marca",
            "pagos__tipo_pago",
        ),
        id=venta_id,
    )

    detalles = venta.detalles.all()
    pago = venta.pagos.select_related("tipo_pago").first()
    subtotal_bruto = sum(item.subtotal for item in detalles)

    config = EmpresaConfig.objects.first()

    if not config:
        config = EmpresaConfig.objects.create()

    context = {
        "venta": venta,
        "detalles": detalles,
        "pago": pago,
        "config": config,
        "subtotal_bruto": subtotal_bruto,
    }

    template_path = "factura_pdf.html"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="recibo_venta_{venta.id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("Tuvimos algunos errores al generar el PDF.")

    return response
