from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404, redirect, render

from administracion.decorators import requiere_permiso
from .forms import CategoriaForm, MarcaForm, ProductoForm, ProveedorForm
from .models import Categoria, Marca, Producto, Proveedor


@requiere_permiso("view_producto")
def catalogo_productos(request):
    productos = Producto.objects.filter(activo=True).select_related(
        "categoria",
        "marca",
        "proveedor",
    ).order_by("nombre")

    return render(request, "catalogo.html", {"productos": productos})


@requiere_permiso("view_producto")
def lista_productos(request):
    productos = Producto.objects.select_related(
        "categoria",
        "marca",
        "proveedor",
    ).all().order_by("nombre")

    return render(request, "lista_productos.html", {"productos": productos})


def _codigo_sugerido():
    ultimo_producto = Producto.objects.filter(codigo__startswith="HER-").order_by("-id").first()

    if ultimo_producto:
        try:
            ultimo_numero = int(ultimo_producto.codigo.split("-")[1])
            siguiente = ultimo_numero + 1
        except (IndexError, ValueError):
            siguiente = 1
    else:
        siguiente = 1

    while True:
        codigo = f"HER-{siguiente:03d}"
        if not Producto.objects.filter(codigo__iexact=codigo).exists():
            return codigo
        siguiente += 1


def _producto_form_context(form=None, producto=None):
    return {
        "form": form,
        "producto": producto,
        "categorias": Categoria.objects.all().order_by("nombre"),
        "proveedores": Proveedor.objects.all().order_by("nombre_empresa"),
        "marcas": Marca.objects.all().order_by("nombre"),
        "codigo_sugerido": form["codigo"].value() if form else _codigo_sugerido(),
    }


@requiere_permiso("add_producto")
def nuevo_producto(request):
    if request.method == "POST":
        data = request.POST.copy()
        data["codigo"] = _codigo_sugerido()

        form = ProductoForm(data, readonly_codigo=True)

        if form.is_valid():
            try:
                with transaction.atomic():
                    producto = form.save(commit=False)
                    producto.stock_actual = 0
                    producto.full_clean()
                    producto.save()

                messages.success(request, f"Producto '{producto.nombre}' creado correctamente.")
                return redirect("lista_productos")

            except IntegrityError:
                messages.error(request, "No se pudo crear el producto porque existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo crear el producto. Verifica los datos e intenta nuevamente.")

        return render(request, "nuevo_producto.html", _producto_form_context(form=form))

    form = ProductoForm(
        initial={
            "codigo": _codigo_sugerido(),
            "stock_minimo": 5,
        },
        readonly_codigo=True,
    )

    return render(request, "nuevo_producto.html", _producto_form_context(form=form))


@requiere_permiso("change_producto")
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        data = request.POST.copy()
        data["codigo"] = producto.codigo

        form = ProductoForm(data, instance=producto, readonly_codigo=True)

        if form.is_valid():
            try:
                with transaction.atomic():
                    producto = form.save(commit=False)
                    producto.full_clean()
                    producto.save()

                messages.success(request, f"Producto '{producto.nombre}' actualizado correctamente.")
                return redirect("lista_productos")

            except IntegrityError:
                messages.error(request, "No se pudo actualizar el producto porque existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo actualizar el producto. Verifica los datos e intenta nuevamente.")

        return render(request, "editar_producto.html", _producto_form_context(form=form, producto=producto))

    form = ProductoForm(instance=producto, readonly_codigo=True)

    return render(request, "editar_producto.html", _producto_form_context(form=form, producto=producto))


@requiere_permiso("delete_producto")
def estado_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_productos")

    try:
        with transaction.atomic():
            producto.activo = not producto.activo
            producto.full_clean()
            producto.save()

        if producto.activo:
            messages.success(request, f"El producto '{producto.nombre}' ha sido reactivado.")
        else:
            messages.warning(request, f"El producto '{producto.nombre}' ha sido dado de baja.")

    except Exception:
        messages.error(request, "No se pudo cambiar el estado del producto.")

    return redirect("lista_productos")


@requiere_permiso("view_categoria")
def lista_categorias(request):
    categorias = Categoria.objects.all().order_by("nombre")
    return render(request, "lista_categorias.html", {"categorias": categorias})


@requiere_permiso("add_categoria")
def nueva_categoria(request):
    form = CategoriaForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    categoria = form.save(commit=False)
                    categoria.full_clean()
                    categoria.save()

                messages.success(request, f"Categoría '{categoria.nombre}' creada correctamente.")
                return redirect("lista_categorias")

            except IntegrityError:
                messages.error(request, "No se pudo crear la categoría porque ya existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo crear la categoría. Verifica los datos e intenta nuevamente.")

    return render(request, "nueva_categoria.html", {"form": form})


@requiere_permiso("change_categoria")
def editar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    form = CategoriaForm(request.POST or None, instance=categoria)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    categoria = form.save(commit=False)
                    categoria.full_clean()
                    categoria.save()

                messages.success(request, f"Categoría '{categoria.nombre}' actualizada correctamente.")
                return redirect("lista_categorias")

            except IntegrityError:
                messages.error(request, "No se pudo actualizar la categoría porque ya existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo actualizar la categoría. Verifica los datos e intenta nuevamente.")

    return render(request, "editar_categoria.html", {"categoria": categoria, "form": form})


@requiere_permiso("delete_categoria")
def eliminar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    nombre = categoria.nombre

    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_categorias")

    try:
        categoria.delete()
        messages.success(request, f"Categoría '{nombre}' eliminada correctamente.")

    except (ProtectedError, RestrictedError):
        messages.error(request, f"No puedes eliminar la categoría '{nombre}' porque tiene productos asociados.")
    except Exception:
        messages.error(request, "No se pudo eliminar la categoría.")

    return redirect("lista_categorias")


@requiere_permiso("view_proveedor")
def lista_proveedores(request):
    proveedores = Proveedor.objects.all().order_by("nombre_empresa")
    return render(request, "lista_proveedores.html", {"proveedores": proveedores})


@requiere_permiso("add_proveedor")
def nuevo_proveedor(request):
    form = ProveedorForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    proveedor = form.save(commit=False)
                    proveedor.full_clean()
                    proveedor.save()

                messages.success(request, f"Proveedor '{proveedor.nombre_empresa}' registrado correctamente.")
                return redirect("lista_proveedores")

            except IntegrityError:
                messages.error(request, "No se pudo registrar el proveedor porque existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo registrar el proveedor. Verifica los datos e intenta nuevamente.")

    return render(request, "nuevo_proveedor.html", {"form": form})


@requiere_permiso("change_proveedor")
def editar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    form = ProveedorForm(request.POST or None, instance=proveedor)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    proveedor = form.save(commit=False)
                    proveedor.full_clean()
                    proveedor.save()

                messages.success(request, f"Proveedor '{proveedor.nombre_empresa}' actualizado correctamente.")
                return redirect("lista_proveedores")

            except IntegrityError:
                messages.error(request, "No se pudo actualizar el proveedor porque existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo actualizar el proveedor. Verifica los datos e intenta nuevamente.")

    return render(request, "editar_proveedor.html", {"proveedor": proveedor, "form": form})


@requiere_permiso("delete_proveedor")
def eliminar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    nombre = proveedor.nombre_empresa

    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_proveedores")

    try:
        proveedor.delete()
        messages.success(request, f"Proveedor '{nombre}' eliminado correctamente.")

    except (ProtectedError, RestrictedError):
        messages.error(request, f"No puedes eliminar al proveedor '{nombre}' porque existen productos o entradas de stock asociadas.")
    except Exception:
        messages.error(request, "No se pudo eliminar el proveedor.")

    return redirect("lista_proveedores")


@requiere_permiso("view_marca")
def lista_marcas(request):
    marcas = Marca.objects.all().order_by("nombre")
    return render(request, "lista_marcas.html", {"marcas": marcas})


@requiere_permiso("add_marca")
def nueva_marca(request):
    form = MarcaForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    marca = form.save(commit=False)
                    marca.full_clean()
                    marca.save()

                messages.success(request, f"Marca '{marca.nombre}' registrada correctamente.")
                return redirect("lista_marcas")

            except IntegrityError:
                messages.error(request, "No se pudo registrar la marca porque ya existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo registrar la marca. Verifica los datos e intenta nuevamente.")

    return render(request, "nueva_marca.html", {"form": form})


@requiere_permiso("change_marca")
def editar_marca(request, marca_id):
    marca = get_object_or_404(Marca, id=marca_id)
    form = MarcaForm(request.POST or None, instance=marca)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    marca = form.save(commit=False)
                    marca.full_clean()
                    marca.save()

                messages.success(request, f"Marca '{marca.nombre}' actualizada correctamente.")
                return redirect("lista_marcas")

            except IntegrityError:
                messages.error(request, "No se pudo actualizar la marca porque ya existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo actualizar la marca. Verifica los datos e intenta nuevamente.")

    return render(request, "editar_marca.html", {"marca": marca, "form": form})


@requiere_permiso("delete_marca")
def eliminar_marca(request, marca_id):
    marca = get_object_or_404(Marca, id=marca_id)
    nombre = marca.nombre

    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_marcas")

    try:
        marca.delete()
        messages.success(request, f"Marca '{nombre}' eliminada correctamente.")

    except (ProtectedError, RestrictedError):
        messages.error(request, f"No puedes eliminar la marca '{nombre}' porque existen productos asociados a ella.")
    except Exception:
        messages.error(request, "No se pudo eliminar la marca.")

    return redirect("lista_marcas")