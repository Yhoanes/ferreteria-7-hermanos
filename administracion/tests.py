from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase

from administracion.models import Usuario


class AdministracionAuthAndRbacTests(TestCase):
    def setUp(self):
        all_perms = Permission.objects.exclude(
            content_type__app_label__in=["admin", "contenttypes", "sessions"]
        )
        self.rol_admin = Group.objects.create(name="Administrador")
        self.rol_admin.permissions.set(all_perms)

        self.rol_restringido = Group.objects.create(name="SoloCatalogo")
        perm_view_prod = Permission.objects.filter(codename="view_producto").first()
        if perm_view_prod:
            self.rol_restringido.permissions.set([perm_view_prod])

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

        self.cajero_email = "cajero@7hermanos.bo"
        self.cajero_pass = "CajeroPass123!"
        u_cajero = User.objects.create_user(
            username=self.cajero_email, email=self.cajero_email, password=self.cajero_pass
        )
        u_cajero.groups.add(self.rol_restringido)
        Usuario.objects.create(
            nombre="Cajero Turno",
            correo=self.cajero_email,
            contrasena="hash",
            rol=self.rol_restringido,
        )

    def test_01_login_page_renders(self):
        client = Client()
        response = client.get("/login/")
        self.assertEqual(response.status_code, 200)

    def test_02_login_invalid_credentials_rejected(self):
        client = Client()
        response = client.post("/login/", {"usuario": self.admin_email, "password": "wrong"})
        self.assertEqual(response.status_code, 200)

    def test_03_login_valid_admin_redirects_and_accesses_dashboard(self):
        client = Client()
        response = client.post(
            "/login/", {"usuario": self.admin_email, "password": self.admin_pass}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.get("/").status_code, 200)

    def test_04_rbac_restricted_role_blocked_from_usuarios_module(self):
        client = Client()
        client.post("/login/", {"usuario": self.cajero_email, "password": self.cajero_pass})
        self.assertEqual(client.get("/usuarios/").status_code, 302)

    def test_05_rbac_restricted_role_allowed_in_catalogo_module(self):
        client = Client()
        client.post("/login/", {"usuario": self.cajero_email, "password": self.cajero_pass})
        self.assertEqual(client.get("/catalogo/").status_code, 200)
