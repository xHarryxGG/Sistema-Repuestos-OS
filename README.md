# Gestión de Inventario y Ventas

Sistema web para administrar inventario, ventas, clientes y reportes de un negocio. Desarrollado con **FastAPI**, **Jinja2** y **SQLite**.

## Características

- **Dashboard** con resumen del día, ganancias y alertas de stock bajo
- **Clientes** — registro y gestión de clientes
- **Productos** — catálogo con precios en USD, stock y categorías
- **Registrar Venta** (Punto de Venta) — cliente opcional, productos, métodos de pago (Pago Móvil, Punto, Efectivo, Divisas), totales en USD y Bs
- **Tasa BCV** — actualización manual y consulta automática desde el Banco Central de Venezuela
- **Ventas** — historial y detalle de ventas
- **Compras** — registro de reposición de inventario
- **Cierre Diario** — resumen y cierre por fecha
- **Reportes** — ganancias (diario/semanal/mensual/anual), más vendidos, métodos de pago
- **Interfaz moderna** con modo claro/oscuro y diseño responsive

## Requisitos

- Python 3.10+

## Instalación

```bash
cd Gestion_inventario
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Ejecutar

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir en el navegador: **http://localhost:8000**

## API de Tasa BCV

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/tasa-bcv` | GET | Obtiene tasa del BCV y la guarda localmente |
| `/api/tasa` | GET | Devuelve la tasa guardada |
| `/api/tasa` | POST | Actualiza la tasa manualmente (`tasa` como form field) |

## Estructura

```
app/
├── main.py           # Aplicación FastAPI
├── database.py       # SQLite y esquema
├── routers/          # Rutas por módulo
├── services/         # BCV, reportes
├── templates/        # Plantillas Jinja2
└── static/           # CSS y JS
data/
└── inventario.db     # Base de datos (se crea al iniciar)
```
