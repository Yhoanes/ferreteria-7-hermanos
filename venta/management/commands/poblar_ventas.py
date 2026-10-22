import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from faker import Faker

# Importamos los modelos necesarios
from venta.models import Cliente, TipoPago, Venta, DetalleVenta, Pago
from producto.models import Producto
from administracion.models import Usuario

class Command(BaseCommand):
    help = 'Puebla la base de datos con clientes, métodos de pago, ventas y detalles de los últimos 7 días.'

    def handle(self, *args, **kwargs):
        fake = Faker('es_ES')
        self.stdout.write(self.style.WARNING('Iniciando la simulación masiva de ventas...'))

        # Verificaciones rápidas de seguridad
        if not Producto.objects.exists():
            self.stdout.write(self.style.ERROR('❌ Error: No puedes crear ventas si no hay productos. Ejecuta primero "poblar_ferreteria".'))
            return
        if not Usuario.objects.exists():
            self.stdout.write(self.style.ERROR('❌ Error: Necesitas usuarios (empleados) para asociar las ventas. Ejecuta primero "poblar_usuarios".'))
            return

        try:
            with transaction.atomic():
                
                # --- 1. CREAR CLIENTES ---
                clientes_creados = []
                for _ in range(20): # Creamos 20 clientes fijos
                    cli, created = Cliente.objects.get_or_create(
                        documento_identidad=fake.unique.numerify(text='#######'),
                        defaults={
                            'nombre': fake.name(),
                            'telefono': fake.numerify(text='7#######'),
                            'direccion': fake.address().replace('\n', ', ')[:250],
                            'activo': True
                        }
                    )
                    clientes_creados.append(cli)
                self.stdout.write(self.style.SUCCESS(f'✅ Se verificaron/crearon {len(clientes_creados)} Clientes.'))

                # --- 2. CREAR TIPOS DE PAGO ---
                metodos = ['EFECTIVO', 'QR', 'TRANSFERENCIA']
                tipos_pago_creados = []
                for nombre in metodos:
                    tipo, created = TipoPago.objects.get_or_create(nombre=nombre)
                    tipos_pago_creados.append(tipo)
                self.stdout.write(self.style.SUCCESS('✅ Métodos de pago (EFECTIVO, QR, TRANSFERENCIA) listos.'))

                # --- 3. CREAR VENTAS HISTÓRICAS (ÚLTIMOS 7 DÍAS) ---
                productos_disponibles = list(Producto.objects.filter(stock_actual__gt=5))
                usuarios_disponibles = list(Usuario.objects.all())
                
                ventas_totales = 40 # Generaremos 40 ventas distribuidas en la semana
                ahora = timezone.now()

                for _ in range(ventas_totales):
                    # Simulamos días atrás (de 0 a 6 días atrás) para rellenar los gráficos semanales
                    dias_atras = random.randint(0, 6)
                    horas_atras = random.randint(1, 12)
                    fecha_venta = ahora - timedelta(days=dias_atras, hours=horas_atras)

                    # Creamos la cabecera de la venta temporalmente con total 0
                    venta = Venta.objects.create(
                        cliente=random.choice(clientes_creados),
                        usuario=random.choice(usuarios_disponibles),
                        total=Decimal('0.00')
                    )

                    # Forzamos la fecha creada para el historial de gráficos
                    Venta.objects.filter(id=venta.id).update(fecha=fecha_venta)

                    # Añadimos entre 1 y 4 productos distintos al detalle de esta venta
                    cantidad_items = random.randint(1, 4)
                    productos_en_venta = random.sample(productos_disponibles, k=min(cantidad_items, len(productos_disponibles)))
                    
                    suma_total = Decimal('0.00')

                    for prod in productos_en_venta:
                        cantidad_comprada = random.randint(1, 3)
                        
                        # Control de Stock rápido para no romper tus validaciones clean()
                        if prod.stock_actual < cantidad_comprada:
                            continue 

                        subtotal_item = prod.precio_venta * cantidad_comprada
                        suma_total += subtotal_item

                        # Guardamos el detalle
                        DetalleVenta.objects.create(
                            venta=venta,
                            producto=prod,
                            cantidad=cantidad_comprada,
                            precio_unitario=prod.precio_venta,
                            subtotal=subtotal_item
                        )

                        # Descontamos el stock físico del producto por la venta
                        prod.stock_actual -= cantidad_comprada
                        prod.save()

                    # Actualizamos el total definitivo de la venta
                    venta.total = suma_total
                    venta.save()

                    # --- 4. REGISTRAR EL PAGO ---
                    # Generamos el pago vinculado correspondiente
                    pago = Pago.objects.create(
                        venta=venta,
                        tipo_pago=random.choice(tipos_pago_creados),
                        monto=suma_total
                    )
                    # Sincronizamos la fecha del pago con la de la venta
                    Pago.objects.filter(id=pago.id).update(fecha_pago=fecha_venta)

                self.stdout.write(self.style.SUCCESS(f'✅ ¡Éxito! Se simularon {ventas_totales} ventas con sus respectivos pagos en los últimos 7 días.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error fatal durante la carga de ventas: {str(e)}'))