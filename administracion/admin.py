from django.contrib import admin
from .models import Usuario, EmpresaConfig

# Registramos solo los modelos que mantenemos en la base de datos
admin.site.register(Usuario)
admin.site.register(EmpresaConfig)