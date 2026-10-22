import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from django.contrib.auth.hashers import make_password
from django.db import transaction
from faker import Faker

# Importamos tu modelo Usuario desde administracion
from administracion.models import Usuario

class Command(BaseCommand):
    help = 'Puebla la base de datos con roles y usuarios falsos para pruebas.'

    def handle(self, *args, **kwargs):
        fake = Faker('es_ES')
        self.stdout.write(self.style.WARNING('Iniciando la carga masiva de usuarios y roles...'))

        try:
            with transaction.atomic():
                
                # --- 1. CREAR ROLES (GRUPOS) ---
                rol_admin, _ = Group.objects.get_or_create(name='Administrador')
                rol_cajero, _ = Group.objects.get_or_create(name='Cajero')
                
                roles_disponibles = [rol_admin, rol_cajero]
                self.stdout.write(self.style.SUCCESS('✅ Roles "Administrador" y "Cajero" verificados/creados.'))

                # --- 2. CREAR USUARIOS FALSOS ---
                usuarios_a_crear = 15 # <-- Cambia este número si quieres más o menos usuarios
                usuarios_creados = 0
                
                # Le pondremos la misma contraseña a todos para que no te vuelvas loco probando
                password_universal = "123456" 
                password_hasheada = make_password(password_universal)

                for i in range(usuarios_a_crear):
                    # Generar datos falsos
                    nombre_completo = fake.name()
                    correo_falso = fake.unique.email()
                    
                    # Asignar rol aleatorio (20% probabilidad de Admin, 80% de Cajero)
                    rol_asignado = random.choices(roles_disponibles, weights=[0.2, 0.8])[0]

                    # A) Crear usuario en el sistema interno de Django
                    user_django = User.objects.create_user(
                        username=correo_falso,
                        email=correo_falso,
                        password=password_universal
                    )
                    user_django.groups.add(rol_asignado)

                    # B) Crear usuario en tu tabla personalizada (Ferretería)
                    usuario_ferreteria = Usuario(
                        nombre=nombre_completo,
                        correo=correo_falso,
                        contrasena=password_hasheada,
                        rol=rol_asignado
                    )
                    usuario_ferreteria.full_clean()
                    usuario_ferreteria.save()
                    
                    usuarios_creados += 1

                self.stdout.write(self.style.SUCCESS(f'✅ ¡Éxito! Se inyectaron {usuarios_creados} Usuarios aleatorios.'))
                self.stdout.write(self.style.WARNING(f'🔑 NOTA: La contraseña para todos estos nuevos usuarios es: {password_universal}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error fatal durante la carga: {str(e)}'))