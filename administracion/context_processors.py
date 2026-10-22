from administracion.models import Usuario

def permisos_usuario(request):
    if request.user.is_authenticated:
        # 1. Si estás logueado como el Admin principal, te habilitamos todos los botones
        if request.user.is_superuser:
            from django.contrib.auth.models import Permission
            todos_los_permisos = Permission.objects.exclude(
                content_type__app_label__in=['admin', 'auth', 'contenttypes', 'sessions']
            ).values_list('codename', flat=True)
            return {'perms_ferreteria': list(todos_los_permisos)}
        
        # 2. Si es un empleado normal (como Andrea)
        try:
            usuario = Usuario.objects.get(correo=request.user.email)
            # Verificamos si tiene un rol asignado
            if usuario.rol:
                # Buscamos los permisos DENTRO de su Rol usando el campo 'codename' de Django
                mis_permisos = usuario.rol.permissions.values_list('codename', flat=True)
                return {'perms_ferreteria': list(mis_permisos)}
        except Usuario.DoesNotExist:
            return {'perms_ferreteria': []}
            
    return {'perms_ferreteria': []}