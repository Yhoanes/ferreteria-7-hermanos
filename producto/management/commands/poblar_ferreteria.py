import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from faker import Faker
from django.db import transaction

# Importamos tus modelos desde la aplicación producto
from producto.models import Categoria, Marca, Proveedor, Producto

class Command(BaseCommand):
    help = 'Puebla la base de datos con categorías, marcas, proveedores y productos falsos para pruebas.'

    def handle(self, *args, **kwargs):
        fake = Faker('es_ES') # Usamos español
        
        self.stdout.write(self.style.WARNING('Iniciando la carga masiva de datos...'))

        try:
            with transaction.atomic(): # Si algo falla, deshace todo para no dejar la DB a medias
                
                # --- 1. CREAR CATEGORÍAS ---
                nombres_categorias = [
                    'Herramientas Manuales', 'Herramientas Eléctricas', 'Plomería', 
                    'Electricidad', 'Pinturas y Accesorios', 'Tornillería', 
                    'Materiales de Construcción', 'Jardinería'
                ]
                categorias_creadas = []
                for nombre in nombres_categorias:
                    cat, created = Categoria.objects.get_or_create(
                        nombre=nombre,
                        defaults={'descripcion': fake.sentence(nb_words=10)}
                    )
                    categorias_creadas.append(cat)
                self.stdout.write(self.style.SUCCESS(f'✅ Se verificaron/crearon {len(categorias_creadas)} Categorías.'))

                # --- 2. CREAR MARCAS ---
                nombres_marcas = [
                    'Stanley', 'DeWalt', 'Makita', 'Bosch', 'Truper', 
                    'Pretul', '3M', 'Sika', 'Tramontina', 'Philips'
                ]
                marcas_creadas = []
                for nombre in nombres_marcas:
                    marca, created = Marca.objects.get_or_create(
                        nombre=nombre,
                        defaults={'descripcion': fake.sentence(nb_words=8)}
                    )
                    marcas_creadas.append(marca)
                self.stdout.write(self.style.SUCCESS(f'✅ Se verificaron/crearon {len(marcas_creadas)} Marcas.'))

                # --- 3. CREAR PROVEEDORES ---
                proveedores_creados = []
                for _ in range(10): # Crearemos 10 proveedores
                    nombre_empresa = fake.company()
                    prov, created = Proveedor.objects.get_or_create(
                        nombre_empresa=nombre_empresa,
                        defaults={
                            'contacto': fake.name(),
                            'telefono': fake.numerify(text='7#######'), # Formato de cel boliviano aprox.
                            'direccion': fake.address().replace('\n', ', ')[:250]
                        }
                    )
                    proveedores_creados.append(prov)
                self.stdout.write(self.style.SUCCESS(f'✅ Se verificaron/crearon {len(proveedores_creados)} Proveedores.'))

                # --- 4. CREAR PRODUCTOS (¡La parte pesada!) ---
                # Nombres genéricos para combinar
                tipos_producto = ['Martillo', 'Taladro', 'Destornillador', 'Llave Inglesa', 'Sierra', 'Cinta Métrica', 'Pegamento', 'Cable', 'Foco', 'Tubo PVC']
                adjetivos = ['Profesional', 'Industrial', 'Básico', 'Premium', 'Reforzado', 'Multiuso']

                productos_a_crear = 50 # <-- ¡CAMBIA ESTE NÚMERO SI QUIERES MÁS O MENOS PRODUCTOS!
                productos_creados_count = 0

                for i in range(productos_a_crear):
                    codigo = f"PRD-{fake.unique.random_int(min=1000, max=99999)}"
                    nombre_prod = f"{random.choice(tipos_producto)} {random.choice(adjetivos)} {random.randint(1, 20)}mm"
                    
                    # Generar precios lógicos (venta mayor que compra)
                    precio_compra = Decimal(random.uniform(10.0, 500.0)).quantize(Decimal('0.01'))
                    margen = Decimal(random.uniform(1.2, 1.8)) # Ganancia del 20% al 80%
                    precio_venta = (precio_compra * margen).quantize(Decimal('0.01'))

                    producto = Producto(
                        codigo=codigo,
                        nombre=nombre_prod,
                        descripcion=fake.text(max_nb_chars=100),
                        precio_compra=precio_compra,
                        precio_venta=precio_venta,
                        stock_actual=random.randint(0, 100),
                        stock_minimo=random.randint(5, 15),
                        categoria=random.choice(categorias_creadas),
                        marca=random.choice(marcas_creadas),
                        proveedor=random.choice(proveedores_creados),
                        activo=random.choices([True, False], weights=[0.9, 0.1])[0] # 90% activos
                    )
                    
                    # Usamos full_clean para respetar tus validaciones antes de guardar
                    producto.full_clean()
                    producto.save()
                    productos_creados_count += 1

                self.stdout.write(self.style.SUCCESS(f'✅ ¡Éxito! Se inyectaron {productos_creados_count} Productos aleatorios.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error fatal durante la carga: {str(e)}'))