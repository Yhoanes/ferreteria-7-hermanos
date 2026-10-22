from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission, User
from django.db import IntegrityError, transaction
from django.db.models import F, RestrictedError, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from producto.models import Producto
from stock.models import DetalleEntrada, DetalleSalida
from venta.models import Cliente, Pago, TipoPago, Venta
from .decorators import requiere_permiso
from .forms import EmpresaConfigForm, UsuarioForm
from .models import EmpresaConfig, Usuario


@login_required
def dashboard(request):
    hoy = timezone.now().date()

    ventas_hoy = Venta.objects.filter(fecha__date=hoy)
    ingresos_hoy = ventas_hoy.aggregate(Sum("total"))["total__sum"] or 0
    cantidad_ventas_hoy = ventas_hoy.count()

    total_clientes = Cliente.objects.filter(activo=True).count()
    total_productos = Producto.objects.filter(stock_actual__gt=0).count()

    productos_agotados = Producto.objects.filter(stock_actual=0).count()
    productos_bajo_stock = Producto.objects.filter(
        stock_actual__gt=0,
        stock_actual__lte=F("stock_minimo"),
    ).order_by("stock_actual")[:6]

    ultimas_ventas = Venta.objects.all().order_by("-fecha")[:5]
    ultimas_entradas = DetalleEntrada.objects.all().order_by("-entrada__fecha")[:5]
    ultimas_salidas = DetalleSalida.objects.all().order_by("-salida__fecha")[:5]

    resumen_pagos = []
    for tipo in TipoPago.objects.all():
        total_metodo = Pago.objects.filter(
            tipo_pago=tipo,
            fecha_pago__date=hoy,
        ).aggregate(Sum("monto"))["monto__sum"] or 0
        resumen_pagos.append({"nombre": tipo.nombre, "total": total_metodo})

    fechas_grafico = []
    totales_grafico = []

    for i in range(6, -1, -1):
        fecha_dia = hoy - timedelta(days=i)
        total_dia = Venta.objects.filter(
            fecha__date=fecha_dia,
        ).aggregate(Sum("total"))["total__sum"] or 0
        fechas_grafico.append(fecha_dia.strftime("%d %b"))
        totales_grafico.append(float(total_dia))

    return render(
        request,
        "index.html",
        {
            "ingresos_hoy": ingresos_hoy,
            "cantidad_ventas_hoy": cantidad_ventas_hoy,
            "total_clientes": total_clientes,
            "total_productos": total_productos,
            "productos_bajo_stock": productos_bajo_stock,
            "productos_agotados": productos_agotados,
            "ultimas_ventas": ultimas_ventas,
            "resumen_pagos": resumen_pagos,
            "fechas_grafico": fechas_grafico,
            "totales_grafico": totales_grafico,
            "ultimas_entradas": ultimas_entradas,
            "ultimas_salidas": ultimas_salidas,
        },
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        usuario = request.POST.get("usuario", "").strip()
        password = request.POST.get("password", "")

        if not usuario or not password:
            messages.error(request, "Usuario y contraseña son obligatorios.")
            return render(request, "login.html")

        user = authenticate(request, username=usuario, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Tu cuenta está desactivada.")
                return render(request, "login.html")

            login(request, user)
            return redirect("home")

        messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@requiere_permiso("view_usuario")
def lista_usuarios(request):
    usuarios = Usuario.objects.select_related("rol").all().order_by("nombre")
    return render(request, "usuarios_lista.html", {"usuarios": usuarios})


@requiere_permiso("add_usuario")
def crear_usuario_ferreteria(request):
    form = UsuarioForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            correo = form.cleaned_data["correo"]
            password = form.cleaned_data["contrasena"]
            rol = form.cleaned_data.get("rol")

            if User.objects.filter(username__iexact=correo).exists() or User.objects.filter(email__iexact=correo).exists():
                messages.error(request, "Ya existe una cuenta con ese correo.")
                return render(
                    request,
                    "usuarios_crear.html",
                    {
                        "form": form,
                        "roles": Group.objects.all().order_by("name"),
                    },
                )

            try:
                with transaction.atomic():
                    user_django = User.objects.create_user(
                        username=correo,
                        email=correo,
                        password=password,
                    )

                    if rol:
                        user_django.groups.add(rol)

                    usuario = form.save(commit=False)
                    usuario.full_clean()
                    usuario.save()

                messages.success(request, f"Usuario {usuario.nombre} creado correctamente.")
                return redirect("lista_usuarios")

            except IntegrityError:
                messages.error(request, "No se pudo crear el usuario porque ya existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo crear el usuario. Verifica los datos e intenta nuevamente.")

    return render(
        request,
        "usuarios_crear.html",
        {
            "form": form,
            "roles": Group.objects.all().order_by("name"),
        },
    )


@requiere_permiso("change_usuario")
def editar_usuario(request, id):
    user_ferreteria = get_object_or_404(Usuario, id=id)
    correo_anterior = user_ferreteria.correo
    form = UsuarioForm(request.POST or None, instance=user_ferreteria, require_password=False)

    if request.method == "POST":
        if form.is_valid():
            correo_nuevo = form.cleaned_data["correo"]
            nuevo_rol = form.cleaned_data.get("rol")
            nueva_password = form.cleaned_data.get("contrasena")

            try:
                with transaction.atomic():
                    user_django = User.objects.filter(username__iexact=correo_anterior).first()

                    if not user_django:
                        user_django = User.objects.filter(email__iexact=correo_anterior).first()

                    if not user_django:
                        messages.error(request, "No se encontró la cuenta de acceso vinculada a este usuario.")
                        return render(
                            request,
                            "usuarios_crear.html",
                            {
                                "user_edit": user_ferreteria,
                                "form": form,
                                "roles": Group.objects.all().order_by("name"),
                            },
                        )

                    existe_otro_user = User.objects.filter(username__iexact=correo_nuevo).exclude(pk=user_django.pk).exists()
                    existe_otro_email = User.objects.filter(email__iexact=correo_nuevo).exclude(pk=user_django.pk).exists()

                    if existe_otro_user or existe_otro_email:
                        messages.error(request, "Ya existe una cuenta de acceso con ese correo.")
                        return render(
                            request,
                            "usuarios_crear.html",
                            {
                                "user_edit": user_ferreteria,
                                "form": form,
                                "roles": Group.objects.all().order_by("name"),
                            },
                        )

                    user_django.username = correo_nuevo
                    user_django.email = correo_nuevo

                    if nueva_password:
                        user_django.set_password(nueva_password)

                    user_django.save()
                    user_django.groups.clear()

                    if nuevo_rol:
                        user_django.groups.add(nuevo_rol)

                    usuario = form.save(commit=False)
                    usuario.full_clean()
                    usuario.save()

                messages.success(request, "Usuario actualizado correctamente.")
                return redirect("lista_usuarios")

            except IntegrityError:
                messages.error(request, "No se pudo actualizar el usuario porque existe un dato duplicado.")
            except Exception:
                messages.error(request, "No se pudo actualizar el usuario. Verifica los datos e intenta nuevamente.")

    return render(
        request,
        "usuarios_crear.html",
        {
            "user_edit": user_ferreteria,
            "form": form,
            "roles": Group.objects.all().order_by("name"),
        },
    )


@requiere_permiso("delete_usuario")
def eliminar_usuario(request, id):
    user_ferreteria = get_object_or_404(Usuario, id=id)
    nombre = user_ferreteria.nombre
    correo = user_ferreteria.correo

    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_usuarios")

    try:
        with transaction.atomic():
            user_ferreteria.delete()
            User.objects.filter(email__iexact=correo).delete()

        messages.success(request, f"Usuario '{nombre}' eliminado del sistema.")

    except RestrictedError:
        messages.error(request, f"No puedes eliminar al usuario '{nombre}' porque ya tiene ventas o movimientos registrados.")
    except Exception:
        messages.error(request, "No se pudo eliminar el usuario.")

    return redirect("lista_usuarios")


@requiere_permiso("view_group")
def lista_roles(request):
    roles = Group.objects.all().order_by("name")
    return render(request, "roles_lista.html", {"roles": roles})


def _permisos_agrupados():
    permisos = Permission.objects.exclude(
        content_type__app_label__in=["admin", "contenttypes", "sessions"]
    ).select_related("content_type").order_by(
        "content_type__app_label",
        "content_type__model",
        "name",
    )

    nombres_modulos = {
        "administracion": "Administración",
        "venta": "Ventas",
        "producto": "Productos",
        "stock": "Stock e Inventario",
        "reporte": "Reportes",
        "auth": "Usuarios, Roles y Permisos",
    }

    grupos = {}

    for permiso in permisos:
        modulo = permiso.content_type.app_label
        nombre_modulo = nombres_modulos.get(modulo, modulo.title())

        if nombre_modulo not in grupos:
            grupos[nombre_modulo] = []

        grupos[nombre_modulo].append(permiso)

    return grupos


@requiere_permiso("add_group")
def crear_rol(request):
    permisos_agrupados = _permisos_agrupados()

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        permisos_ids = request.POST.getlist("permisos")

        if not nombre:
            messages.error(request, "El nombre del rol es obligatorio.")
        elif len(nombre) < 3:
            messages.error(request, "El nombre del rol debe tener al menos 3 caracteres.")
        elif Group.objects.filter(name__iexact=nombre).exists():
            messages.error(request, "Ya existe un rol con ese nombre.")
        else:
            try:
                with transaction.atomic():
                    nuevo_rol = Group.objects.create(name=nombre)
                    permisos_seleccionados = Permission.objects.filter(id__in=permisos_ids)
                    nuevo_rol.permissions.set(permisos_seleccionados)

                messages.success(request, f"Rol '{nombre}' creado exitosamente.")
                return redirect("lista_roles")

            except IntegrityError:
                messages.error(request, "Ya existe un rol con ese nombre.")
            except Exception:
                messages.error(request, "No se pudo crear el rol.")

    return render(
        request,
        "rol_formulario.html",
        {
            "permisos_agrupados": permisos_agrupados,
            "accion": "Crear",
        },
    )


@requiere_permiso("change_group")
def editar_rol(request, id):
    rol = get_object_or_404(Group, id=id)
    permisos_agrupados = _permisos_agrupados()

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        permisos_ids = request.POST.getlist("permisos")

        if not nombre:
            messages.error(request, "El nombre del rol es obligatorio.")
        elif len(nombre) < 3:
            messages.error(request, "El nombre del rol debe tener al menos 3 caracteres.")
        elif Group.objects.filter(name__iexact=nombre).exclude(pk=rol.pk).exists():
            messages.error(request, "Ya existe otro rol con ese nombre.")
        else:
            try:
                with transaction.atomic():
                    rol.name = nombre
                    rol.save()
                    permisos_seleccionados = Permission.objects.filter(id__in=permisos_ids)
                    rol.permissions.set(permisos_seleccionados)

                messages.success(request, f"Rol '{nombre}' actualizado.")
                return redirect("lista_roles")

            except IntegrityError:
                messages.error(request, "Ya existe otro rol con ese nombre.")
            except Exception:
                messages.error(request, "No se pudo actualizar el rol.")

    return render(
        request,
        "rol_formulario.html",
        {
            "rol": rol,
            "permisos_agrupados": permisos_agrupados,
            "accion": "Editar",
        },
    )


@requiere_permiso("delete_group")
def eliminar_rol(request, id):
    rol = get_object_or_404(Group, id=id)
    nombre = rol.name

    if request.method != "POST":
        messages.error(request, "Solicitud no válida.")
        return redirect("lista_roles")

    try:
        rol.delete()
        messages.success(request, f"Rol '{nombre}' eliminado correctamente.")
    except RestrictedError:
        messages.error(request, f"No puedes eliminar el rol '{nombre}' porque está relacionado con usuarios.")
    except Exception:
        messages.error(request, "No se pudo eliminar el rol.")

    return redirect("lista_roles")


@requiere_permiso("change_empresaconfig")
def configuracion_empresa(request):
    config = EmpresaConfig.objects.first()

    if not config:
        config = EmpresaConfig.objects.create()

    form = EmpresaConfigForm(request.POST or None, instance=config)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    config = form.save(commit=False)
                    config.actualizado_por = Usuario.objects.filter(correo__iexact=request.user.email).first()
                    config.full_clean()
                    config.save()

                messages.success(request, "Los datos de la empresa se han actualizado correctamente.")
                return redirect("configuracion_empresa")

            except Exception:
                messages.error(request, "No se pudo actualizar la configuración de la empresa.")

    return render(
        request,
        "configuracion_empresa.html",
        {
            "config": config,
            "form": form,
        },
    )