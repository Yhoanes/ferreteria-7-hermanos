# Ferretería 7 Hermanos - Arquitectura del Proyecto

## 1. Objetivos del Proyecto
- **Gestión Integral del Negocio:** Plataforma centralizada para la administración operativa, comercial y logística de Ferretería 7 Hermanos.
- **Control de Inventario y Existencias:** Trazabilidad completa de entradas, salidas y ajustes de stock en tiempo real.
- **Operaciones Comerciales:** Emisión de ventas, cálculo dinámico de descuentos, soporte para múltiples modalidades de pago y administración de clientes.
- **Reportería y Analítica:** Reportes financieros, de inventario y de desempeño comercial con exportación PDF/Excel.

## 2. Arquitectura del Sistema (Django / Python)

### 2.1 Aplicaciones Principales
- **`producto/` (Inventario):** Catálogo de productos, categorización, marcas, unidades de medida y proveedores.
- **`stock/`:** Control transaccional de movimientos de existencias (entradas, salidas, transferencias y comando `poblar_stock`).
- **`venta/`:** Flujo de ventas, facturación, cuentas por cobrar, clientes, descuentos y formas de pago.
- **`administracion/`:** Control de acceso, perfiles de usuario, roles, permisos y parámetros globales.
- **`reporte/`:** Generación y renderizado de reportes consolidados y analítica de negocio.

### 2.2 Capa de Presentación y Núcleo
- **`templates/` y `static/`:** Plantillas HTML de Django, hojas de estilo CSS, scripts JavaScript e imágenes.
- **`ferreteria_sys/`:** Configuración central de Django (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).
- **Persistencia de Datos:** PostgreSQL (`psycopg2-binary`) en producción y SQLite en desarrollo/pruebas.
- **Librerías Clave:** `reportlab` y `xhtml2pdf` (PDF), `openpyxl` (Excel), `cryptography` y `pyHanko` (firma/seguridad documental).
