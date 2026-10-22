import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase
from django.utils import timezone

from administracion.models import Usuario
from producto.models import Categoria, Marca, Producto, Proveedor
from venta.models import Cliente, Descuento, TipoPago, Venta


class VentaPosAndPdfTests(TestCase):
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
        self.usuario = Usuario.objects.create(
            nombre="Admin General",
            correo=self.admin_email,
            contrasena="hash",
            rol=self.rol_admin,
        )

        cat = Categoria.objects.create(nombre="Construccion", descripcion="Cat")
        marca = Marca.objects.create(nombre="Stanley", descripcion="Marca")
        prov = Proveedor.objects.create(
            nombre_empresa="Proveedora Industrial",
            contacto="Pedro Rojas",
            telefono="70055555",
            direccion="Av. Banzer",
        )
        self.prod = Producto.objects.create(
            codigo="CON-01",
            nombre="Taladro Percutor 800W",
            descripcion="Uso pesado",
            precio_compra=Decimal("350.00"),
            precio_venta=Decimal("500.00"),
            stock_actual=20,
            stock_minimo=5,
            categoria=cat,
            marca=marca,
            proveedor=prov,
        )

        self.client = Client()
        self.client.post("/login/", {"usuario": self.admin_email, "password": self.admin_pass})

    def test_16_ajax_crear_cliente_returns_valid_id(self):
        r_cli = self.client.post(
            "/clientes/ajax-crear/",
            {
                "nombre": "Constructora Del Oriente",
                "documento_identidad": "9988776015",
                "telefono": "77001122",
                "direccion": "Parque Industrial",
            },
        )
        self.assertEqual(r_cli.status_code, 200)
        cli_id = json.loads(r_cli.content)["id"]
        self.assertTrue(Cliente.objects.filter(id=cli_id).exists())

    def test_17_create_tipo_pago(self):
        self.client.post("/tipos-pago/nuevo/", {"nombre": "QR Simple"})
        self.assertTrue(TipoPago.objects.filter(nombre="QR Simple").exists())

    def test_18_create_descuento_promocional(self):
        now = timezone.now()
        self.client.post(
            "/descuentos/nuevo/",
            {
                "nombre": "Promo 10%",
                "porcentaje": "10.00",
                "fecha_inicio": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "fecha_fin": (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M"),
            },
        )
        self.assertTrue(Descuento.objects.filter(nombre="Promo 10%").exists())

    def test_19_registrar_venta_calculates_discount_and_deducts_stock(self):
        cli = Cliente.objects.create(
            nombre="Cliente Corporativo",
            documento_identidad="10203040",
            telefono="70011111",
            direccion="Centro",
        )
        tp = TipoPago.objects.create(nombre="Efectivo")
        now = timezone.now()
        desc = Descuento.objects.create(
            nombre="Promo 10%",
            porcentaje=Decimal("10.00"),
            fecha_inicio=now - timedelta(days=1),
            fecha_fin=now + timedelta(days=5),
        )
        carrito = json.dumps([{"id_producto": self.prod.id, "cantidad": 4}])
        r_venta = self.client.post(
            "/venta/nueva/",
            {
                "cliente": str(cli.id),
                "tipo_pago": str(tp.id),
                "descuento": str(desc.id),
                "carrito_datos": carrito,
            },
        )
        self.assertEqual(r_venta.status_code, 302)
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_actual, 16)
        venta = Venta.objects.get(cliente=cli)
        self.assertEqual(venta.total, Decimal("1800.00"))

    def test_20_generar_recibo_pdf_returns_valid_pdf_document(self):
        cli = Cliente.objects.create(
            nombre="Cliente Recibo",
            documento_identidad="55667788",
            telefono="70022222",
            direccion="Av. Busch",
        )
        tp = TipoPago.objects.create(nombre="Transferencia")
        carrito = json.dumps([{"id_producto": self.prod.id, "cantidad": 1}])
        self.client.post(
            "/venta/nueva/",
            {
                "cliente": str(cli.id),
                "tipo_pago": str(tp.id),
                "descuento": "",
                "carrito_datos": carrito,
            },
        )
        venta = Venta.objects.get(cliente=cli)
        r_pdf = self.client.get(f"/venta/{venta.id}/recibo/")
        self.assertEqual(r_pdf.status_code, 200)
        self.assertTrue(r_pdf.content.startswith(b"%PDF-"))
