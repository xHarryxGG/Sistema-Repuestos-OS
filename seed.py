"""Script para cargar datos de ejemplo."""
from app.database import init_db, get_db

init_db()

PRODUCTOS = [
    ("ARZ001", "Arroz 1kg", "Arroz blanco premium", "Alimentos", 1.50, 1.00, 50),
    ("ACE001", "Aceite 1L", "Aceite vegetal", "Alimentos", 3.20, 2.50, 30),
    ("LEC001", "Leche 1L", "Leche entera", "Lacteos", 1.80, 1.30, 40),
    ("PAN001", "Pan de Sandwich", "Paquete 10 unidades", "Panaderia", 2.00, 1.50, 25),
    ("COC001", "Coca Cola 2L", "Refresco", "Bebidas", 2.50, 1.80, 35),
    ("JAB001", "Jabón de Baño", "Jabón antibacterial", "Limpieza", 1.20, 0.80, 60),
    ("DET001", "Detergente 1kg", "Detergente en polvo", "Limpieza", 4.50, 3.20, 20),
    ("PAP001", "Papel Higiénico", "Paquete 4 rollos", "Limpieza", 3.00, 2.00, 45),
]

CLIENTES = [
    ("María González", "V-12345678", "0414-1234567", "maria@email.com"),
    ("Juan Pérez", "V-87654321", "0424-9876543", "juan@email.com"),
    ("Ana Rodríguez", "V-11223344", "0412-5551234", ""),
]

with get_db() as conn:
    for codigo, nombre, desc, cat, precio, costo, stock in PRODUCTOS:
        conn.execute(
            """INSERT OR IGNORE INTO productos (codigo, nombre, descripcion, categoria, precio_usd, costo_usd, stock)
               VALUES (?,?,?,?,?,?,?)""",
            (codigo, nombre, desc, cat, precio, costo, stock),
        )
    for nombre, cedula, tel, email in CLIENTES:
        conn.execute(
            "INSERT OR IGNORE INTO clientes (nombre, cedula, telefono, email) VALUES (?,?,?,?)",
            (nombre, cedula, tel, email),
        )

print("Datos de ejemplo cargados correctamente.")
