import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from faker import Faker

# Importamos los modelos necesarios
from stock.models import EntradaStock, DetalleEntrada, SalidaStock, DetalleSalida
from producto.models import Producto, Proveedor
from administracion.models import Usuario

class Command(BaseCommand):
    help = 'Puebla la base de datos con entradas (compras) y salidas (mermas/uso) de stock.'

    def handle(self, *args, **kwargs):
        fake = Faker('es_ES')
        self.stdout.write(self.style.WARNING('Iniciando la simulación masiva de movimientos de almacén...'))

        # Verificaciones de seguridad
        if not Producto.objects.exists() or not Proveedor.objects.exists():
            self.stdout.write(self.style.ERROR('❌ Error: Faltan productos o proveedores. Ejecuta "poblar_ferreteria".'))
            return
        if not Usuario.objects.exists():
            self.stdout.write(self.style.ERROR('❌ Error: Faltan usuarios. Ejecuta "poblar_usuarios".'))
            return

        try:
            with transaction.atomic():
                
                productos = list(Producto.objects.all())
                proveedores = list(Proveedor.objects.all())
                usuarios = list(Usuario.objects.all())
                ahora = timezone.now()

                # --- 1. SIMULAR ENTRADAS DE STOCK (COMPRAS A PROVEEDORES) ---
                entradas_totales = 15
                for _ in range(entradas_totales):
                    dias_atras = random.randint(1, 30)
                    fecha_movimiento = ahora - timedelta(days=dias_atras, hours=random.randint(1, 12))

                    entrada = EntradaStock.objects.create(
                        proveedor=random.choice(proveedores),
                        usuario=random.choice(usuarios),
                        observacion=random.choice(["Llegó completo", "Cajas algo golpeadas", "Entrega regular", ""])
                    )
                    # Forzar la fecha
                    EntradaStock.objects.filter(id=entrada.id).update(fecha=fecha_movimiento)

                    # Añadir productos a esta entrada
                    productos_entrada = random.sample(productos, k=random.randint(2, 6))
                    for prod in productos_entrada:
                        cantidad_ingresada = random.randint(10, 50)
                        
                        DetalleEntrada.objects.create(
                            entrada=entrada,
                            producto=prod,
                            cantidad=cantidad_ingresada,
                            costo_unitario=prod.precio_compra # Usamos el costo base del producto
                        )
                        # Aumentar el stock real del producto
                        prod.stock_actual += cantidad_ingresada
                        prod.save()

                self.stdout.write(self.style.SUCCESS(f'✅ Se registraron {entradas_totales} Entradas de Stock.'))


                # --- 2. SIMULAR SALIDAS DE STOCK (MERMAS / USO INTERNO) ---
                salidas_totales = 10
                motivos_salida = ["Producto Dañado", "Uso Interno", "Vencimiento", "Pérdida/Robo", "Muestra para cliente"]

                # Refrescamos la lista de productos porque las entradas anteriores ya debieron sumarles stock
                productos_actualizados = list(Producto.objects.filter(stock_actual__gt=0))

                # Si de pura casualidad seguimos sin stock (muy raro), abortamos las salidas pero avisamos
                if not productos_actualizados:
                    self.stdout.write(self.style.WARNING('⚠️ No se pudieron generar Salidas (mermas) porque ningún producto tiene stock.'))
                else:
                    for _ in range(salidas_totales):
                        dias_atras = random.randint(1, 15)
                        fecha_movimiento = ahora - timedelta(days=dias_atras, hours=random.randint(1, 12))

                        salida = SalidaStock.objects.create(
                            usuario=random.choice(usuarios),
                            motivo=random.choice(motivos_salida)
                        )
                        # Forzar la fecha
                        SalidaStock.objects.filter(id=salida.id).update(fecha=fecha_movimiento)

                        # Elegimos 1 a 3 productos de los que SÍ sabemos que tienen stock
                        productos_salida = random.sample(productos_actualizados, k=min(random.randint(1, 3), len(productos_actualizados)))
                        
                        for prod in productos_salida:
                            # Sacamos una cantidad pequeña (1 a 5) pero siempre respetando el límite
                            cantidad_salida = random.randint(1, min(5, prod.stock_actual))
                            
                            DetalleSalida.objects.create(
                                salida=salida,
                                producto=prod,
                                cantidad=cantidad_salida
                            )
                            # Disminuir el stock real del producto
                            prod.stock_actual -= cantidad_salida
                            prod.save()

                    self.stdout.write(self.style.SUCCESS(f'✅ Se registraron {salidas_totales} Salidas de Stock (Mermas).'))
                
                self.stdout.write(self.style.SUCCESS('✅ ¡Dashboard completamente integrado y con datos vivos!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error fatal durante la carga de stock: {str(e)}'))