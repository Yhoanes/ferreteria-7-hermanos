from django.contrib import admin
from .models import Categoria, Proveedor, Producto

# Le decimos a Django que muestre estas 3 tablas en tu panel
admin.site.register(Categoria)
admin.site.register(Proveedor)
admin.site.register(Producto)