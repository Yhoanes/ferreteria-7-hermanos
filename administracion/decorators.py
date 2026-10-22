from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def requiere_permiso(nombre_permiso):
    def decorador(view_func):
        @wraps(view_func)
        def wrapper_func(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                messages.error(request, "Debes iniciar sesión para acceder al sistema.")
                return redirect("login")

            if not user.is_active:
                messages.error(request, "Tu cuenta está desactivada.")
                return redirect("login")

            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            from .models import Usuario

            usuario_ferreteria = Usuario.objects.select_related("rol").filter(
                correo__iexact=user.email
            ).first()

            if not usuario_ferreteria:
                messages.error(request, "Tu cuenta no está vinculada al sistema interno.")
                return redirect("login")

            if not usuario_ferreteria.rol:
                messages.error(request, "Tu cuenta no tiene un rol asignado.")
                return redirect("home")

            tiene_permiso = usuario_ferreteria.rol.permissions.filter(
                codename=nombre_permiso
            ).exists()

            if not tiene_permiso:
                messages.error(request, "No tienes permiso para realizar esta acción.")
                return redirect("home")

            return view_func(request, *args, **kwargs)

        return wrapper_func

    return decorador