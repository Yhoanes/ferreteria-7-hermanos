from django.contrib import admin
from .models import EntradaStock, DetalleEntrada, SalidaStock, DetalleSalida

admin.site.register(EntradaStock)
admin.site.register(DetalleEntrada)
admin.site.register(SalidaStock)
admin.site.register(DetalleSalida)