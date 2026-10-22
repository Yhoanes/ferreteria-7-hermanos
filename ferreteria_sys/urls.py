from django.contrib import admin
from django.urls import path
from producto import views
from administracion import views as admin_views 
from venta import views as venta_views
from stock import views as stock_views 
from reporte import views as reporte_views
from venta.views import lista_clientes, nuevo_cliente, editar_cliente, estado_cliente, crear_cliente_ajax

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', admin_views.dashboard, name='home'), 
    path('configuracion/', admin_views.configuracion_empresa, name='configuracion_empresa'),
    path('venta/nueva/', venta_views.realizar_venta, name='nueva_venta'),
    path('venta/historial/', venta_views.historial_ventas, name='historial_ventas'),
    path('venta/detalle/<int:venta_id>/', venta_views.detalle_venta, name='detalle_venta'),
    path('reportes/', reporte_views.reporte_ventas, name='reporte_ventas'),
    path('venta/<int:venta_id>/recibo/', venta_views.generar_recibo_pdf, name='generar_recibo_pdf'),
    
    #login
    path('login/', admin_views.login_view, name='login'),
    path('logout/', admin_views.logout_view, name='logout'),
    
    #usuario
    path('usuarios/', admin_views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/nuevo/', admin_views.crear_usuario_ferreteria, name='crear_usuario'),
    path('usuarios/editar/<int:id>/', admin_views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:id>/', admin_views.eliminar_usuario, name='eliminar_usuario'),
    
    #salida stock
    path('stock/salidas/', stock_views.lista_salidas, name='lista_salidas'),
    path('stock/salidas/nueva/', stock_views.registrar_salida, name='registrar_salida'),
    
    #entrada de stock
    path('stock/entradas/', stock_views.lista_entradas, name='lista_entradas'),
    path('stock/entradas/nueva/', stock_views.registrar_entrada, name='registrar_entrada'),
    
    # roles (grupos)
    path('roles/', admin_views.lista_roles, name='lista_roles'),
    path('roles/nuevo/', admin_views.crear_rol, name='crear_rol'),
    path('roles/editar/<int:id>/', admin_views.editar_rol, name='editar_rol'),
    path('roles/eliminar/<int:id>/', admin_views.eliminar_rol, name='eliminar_rol'),
    
    #clientes
    path('clientes/', lista_clientes, name='lista_clientes'),
    path('clientes/nuevo/', nuevo_cliente, name='nuevo_cliente'),
    path('clientes/editar/<int:cliente_id>/', editar_cliente, name='editar_cliente'),
    path('clientes/estado/<int:cliente_id>/', estado_cliente, name='estado_cliente'),
    path('clientes/ajax-crear/', crear_cliente_ajax, name='crear_cliente_ajax'),
    
    # Ruta del catálogo de consulta
    path('catalogo/', views.catalogo_productos, name='catalogo'),
    
    # Rutas administrativas del CRUD
    path('productos/gestion/', views.lista_productos, name='lista_productos'),
    path('productos/nuevo/', views.nuevo_producto, name='nuevo_producto'),
    path('productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('productos/estado/<int:producto_id>/', views.estado_producto, name='estado_producto'),
    
    # Categorías
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/nueva/', views.nueva_categoria, name='nueva_categoria'),
    path('categorias/editar/<int:categoria_id>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/eliminar/<int:categoria_id>/', views.eliminar_categoria, name='eliminar_categoria'),
    
    # proveedores
    path('proveedores/', views.lista_proveedores, name='lista_proveedores'),
    path('proveedores/nuevo/', views.nuevo_proveedor, name='nuevo_proveedor'), 
    path('proveedores/editar/<int:proveedor_id>/', views.editar_proveedor, name='editar_proveedor'),
    path('proveedores/eliminar/<int:proveedor_id>/', views.eliminar_proveedor, name='eliminar_proveedor'),
    
    # Tipos de Pago
    path('tipos-pago/', venta_views.lista_tipos_pago, name='lista_tipos_pago'),
    path('tipos-pago/nuevo/', venta_views.nuevo_tipo_pago, name='nuevo_tipo_pago'),
    path('tipos-pago/editar/<int:tipo_id>/', venta_views.editar_tipo_pago, name='editar_tipo_pago'),
    path('tipos-pago/eliminar/<int:tipo_id>/', venta_views.eliminar_tipo_pago, name='eliminar_tipo_pago'),
    
    # Descuentos
    path('descuentos/', venta_views.lista_descuentos, name='lista_descuentos'),
    path('descuentos/nuevo/', venta_views.nuevo_descuento, name='nuevo_descuento'),
    path('descuentos/editar/<int:descuento_id>/', venta_views.editar_descuento, name='editar_descuento'),
    path('descuentos/eliminar/<int:descuento_id>/', venta_views.eliminar_descuento, name='eliminar_descuento'),

    # categoria
    path('marcas/', views.lista_marcas, name='lista_marcas'),
    path('marcas/nueva/', views.nueva_marca, name='nueva_marca'),
    path('marcas/editar/<int:marca_id>/', views.editar_marca, name='editar_marca'),
    path('marcas/eliminar/<int:marca_id>/', views.eliminar_marca, name='eliminar_marca'),

]