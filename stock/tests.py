from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase

from administracion.models import Usuario
from producto.models import Categoria, Marca, Producto, Proveedor


class StockInventoryTests(TestCase):
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

        self.cat = Categoria.objects.create(nombre="Electricidad", descripcion="Cat")
        self.marca = Marca.objects.create(nombre="DeWalt", descripcion="Marca")
        self.prov = Proveedor.objects.create(
            nombre_empresa="Importadora Oriental",
            contacto="Luis Suarez",
            telefono="70012345",
            direccion="Parque Industrial",
        )
        self.prod = Producto.objects.create(
            codigo="EL-100",
            nombre="Amoladora Angular 900W",
            descripcion="4.5 pulgadas",
            precio_compra=Decimal("280.00"),
            precio_venta=Decimal("420.00"),
            stock_actual=0,
            stock_minimo=5,
            categoria=self.cat,
            marca=self.marca,
            proveedor=self.prov,
        )

        self.client = Client()
        self.client.post("/login/", {"usuario": self.admin_email, "password": self.admin_pass})

    def test_11_entrada_stock_increments_stock_actual(self):
        self.client.post(
            "/stock/entradas/nueva/",
            {
                "proveedor": str(self.prov.id),
                "producto": str(self.prod.id),
                "cantidad": "25",
                "costo": "280.00",
                "observacion": "Ingreso inicial",
            },
        )
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_actual, 25)

    def test_12_salida_stock_decrements_stock_actual(self):
        self.prod.stock_actual = 25
        self.prod.save()
        self.client.post(
            "/stock/salidas/nueva/",
            {"producto": str(self.prod.id), "cantidad": "5", "motivo": "Uso Interno"},
        )
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_actual, 20)

    def test_13_salida_stock_exceeding_available_is_rejected(self):
        self.prod.stock_actual = 20
        self.prod.save()
        self.client.post(
            "/stock/salidas/nueva/",
            {"producto": str(self.prod.id), "cantidad": "99", "motivo": "Merma"},
        )
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_actual, 20)

    def test_14_multiple_stock_entries_accumulate_correctly(self):
        for qty in ("10", "15"):
            self.client.post(
                "/stock/entradas/nueva/",
                {
                    "proveedor": str(self.prov.id),
                    "producto": str(self.prod.id),
                    "cantidad": qty,
                    "costo": "280.00",
                    "observacion": "Lote adicional",
                },
            )
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_actual, 25)

    def test_15_stock_entradas_list_renders(self):
        response = self.client.get("/stock/entradas/")
        self.assertEqual(response.status_code, 200)
