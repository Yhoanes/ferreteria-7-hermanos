from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase

from administracion.models import Usuario


class ReporteAnalyticsAndExcelTests(TestCase):
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

    def _verify_report_html_and_excel(self, tipo: str):
        r_html = self.client.get(f"/reportes/?tipo={tipo}")
        self.assertEqual(r_html.status_code, 200)
        r_xlsx = self.client.get(f"/reportes/?tipo={tipo}&exportar_excel=1")
        self.assertEqual(r_xlsx.status_code, 200)
        self.assertTrue(r_xlsx.content.startswith(b"PK\x03\x04"))

    def test_21_reporte_ventas_html_and_xlsx(self):
        self._verify_report_html_and_excel("ventas")

    def test_22_reporte_inventario_html_and_xlsx(self):
        self._verify_report_html_and_excel("inventario")

    def test_23_reporte_top_productos_html_and_xlsx(self):
        self._verify_report_html_and_excel("top_productos")

    def test_24_reporte_vendedores_html_and_xlsx(self):
        self._verify_report_html_and_excel("vendedores")

    def test_25_reporte_pagos_html_and_xlsx(self):
        self._verify_report_html_and_excel("pagos")
