from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase

from administracion.models import Usuario
from producto.models import Categoria, Marca, Producto, Proveedor


class ProductoCatalogTests(TestCase):
    def setUp(self):
        all_perms = Permission.objects.exclude(
            content_type__app_label__in=["admin", "contenttypes", "sessions"]
        )
        self.rol_admin = Group.objects.create(name="Administrador")
        self.rol_admin.permissions.set(all_perms)

        self.admin_email = "admin@7hermanos.bo"
        self.admin_pass = "AdminPass123!"
        u_admin = User.objects.create_user(
            username=self.admin_email, email=self.admin_email, password=self.admin_pass
        )
        u_admin.groups.add(self.rol_admin)
        Usuario.objects.create(
            nombre="Admin General",
            correo=self.admin_email,
            contrasena="hash",
            rol=self.rol_admin,
        )
        self.client = Client()
        self.client.post("/login/", {"usuario": self.admin_email, "password": self.admin_pass})

    def test_06_create_categoria(self):
        self.client.post(
            "/categorias/nueva/",
            {"nombre": "Herramientas Electricas", "descripcion": "Categoria industrial"},
        )
        self.assertTrue(Categoria.objects.filter(nombre="Herramientas Electricas").exists())

    def test_07_create_marca(self):
        self.client.post(
            "/marcas/nueva/",
            {"nombre": "Bosch Industrial", "descripcion": "Linea profesional"},
        )
        self.assertTrue(Marca.objects.filter(nombre="Bosch Industrial").exists())

    def test_08_create_proveedor(self):
        self.client.post(
            "/proveedores/nuevo/",
            {
                "nombre_empresa": "Importadora Cruz del Sur",
                "contacto": "Carlos Gomez",
                "telefono": "+591 70011223",
                "direccion": "Av. Cristo Redentor Km 4",
            },
        )
        self.assertTrue(
            Proveedor.objects.filter(nombre_empresa="Importadora Cruz del Sur").exists()
        )

    def test_09_create_producto_initializes_zero_stock(self):
        cat = Categoria.objects.create(nombre="Ferreteria General", descripcion="Base")
        marca = Marca.objects.create(nombre="Truper", descripcion="Base")
        prov = Proveedor.objects.create(
            nombre_empresa="Distribuidora Andina",
            contacto="Ana Perez",
            telefono="70000001",
            direccion="Zona Norte",
        )
        self.client.post(
            "/productos/nuevo/",
            {
                "codigo": "HER-001",
                "nombre": "Taladro Percutor 800W",
                "descripcion": "Uso pesado",
                "precio_compra": "350.00",
                "precio_venta": "500.00",
                "stock_minimo": "5",
                "categoria": str(cat.id),
                "marca": str(marca.id),
                "proveedor": str(prov.id),
            },
        )
        prod = Producto.objects.get(nombre="Taladro Percutor 800W")
        self.assertEqual(prod.stock_actual, 0)
        self.assertEqual(prod.precio_venta, Decimal("500.00"))

    def test_10_catalogo_view_renders_products(self):
        response = self.client.get("/catalogo/")
        self.assertEqual(response.status_code, 200)
