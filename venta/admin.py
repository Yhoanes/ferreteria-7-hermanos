from django.contrib import admin
from .models import Cliente, TipoPago, Descuento, Venta, DetalleVenta, Pago

admin.site.register(Cliente)
admin.site.register(TipoPago)
admin.site.register(Descuento)
admin.site.register(Venta)
admin.site.register(DetalleVenta)
admin.site.register(Pago)