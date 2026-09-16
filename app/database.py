import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = Path(__file__).parent.parent / "data" / "inventario.db"
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")



def is_postgres() -> bool:
    url = DATABASE_URL or ""
    return "postgres://" in url or "postgresql://" in url


class PostgresCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, query: str, params: tuple | list = ()):
        pg_query = query.replace("?", "%s")
        is_insert = pg_query.strip().upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in pg_query.upper()

        if is_insert and not has_returning:
            pg_query = pg_query.rstrip("; ") + " RETURNING id;"

        self._cursor.execute(pg_query, params or ())

        if is_insert:
            try:
                row = self._cursor.fetchone()
                if row and "id" in row:
                    self.lastrowid = row["id"]
            except Exception:
                pass
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class PostgresConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        import psycopg2.extras
        return PostgresCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))

    def execute(self, query: str, params: tuple | list = ()):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def executescript(self, script: str):
        with self._conn.cursor() as cur:
            cur.execute(script)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_connection():
    if is_postgres():
        import psycopg2
        url = DATABASE_URL
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        return PostgresConnectionWrapper(conn)
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    if is_postgres():
        # En Supabase PostgreSQL, la estructura se crea ejecutando supabase_schema.sql
        return

    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                cedula TEXT,
                telefono TEXT,
                email TEXT,
                direccion TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                categoria TEXT,
                precio_usd REAL NOT NULL DEFAULT 0,
                costo_usd REAL NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT 0,
                stock_minimo INTEGER DEFAULT 5,
                activo INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER REFERENCES clientes(id),
                total_usd REAL NOT NULL DEFAULT 0,
                total_bs REAL NOT NULL DEFAULT 0,
                subtotal_usd REAL NOT NULL DEFAULT 0,
                iva_usd REAL NOT NULL DEFAULT 0,
                subtotal_bs REAL NOT NULL DEFAULT 0,
                iva_bs REAL NOT NULL DEFAULT 0,
                tasa_cambio REAL NOT NULL DEFAULT 1,
                notas TEXT,
                fecha TEXT DEFAULT (datetime('now', 'localtime')),
                cerrada INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS venta_detalles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                producto_id INTEGER NOT NULL REFERENCES productos(id),
                cantidad INTEGER NOT NULL,
                precio_unitario_usd REAL NOT NULL,
                subtotal_usd REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS venta_pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                metodo_pago TEXT NOT NULL,
                monto_usd REAL NOT NULL DEFAULT 0,
                monto_bs REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor TEXT,
                total_usd REAL NOT NULL DEFAULT 0,
                notas TEXT,
                fecha TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS compra_detalles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                compra_id INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
                producto_id INTEGER NOT NULL REFERENCES productos(id),
                cantidad INTEGER NOT NULL,
                precio_unitario_usd REAL NOT NULL,
                subtotal_usd REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cierres_diarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL UNIQUE,
                total_ventas_usd REAL DEFAULT 0,
                total_ventas_bs REAL DEFAULT 0,
                total_efectivo_usd REAL DEFAULT 0,
                total_pago_movil_bs REAL DEFAULT 0,
                total_punto_bs REAL DEFAULT 0,
                total_divisas_usd REAL DEFAULT 0,
                num_ventas INTEGER DEFAULT 0,
                notas TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_cambio', '36.50');
            INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('nombre_negocio', 'Mi Negocio');

            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entidad TEXT NOT NULL,
                entidad_id INTEGER NOT NULL,
                accion TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                datos_anteriores TEXT,
                datos_nuevos TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)

        # Migraciones seguras para bases de datos existentes en SQLite
        for col in ["subtotal_usd", "iva_usd", "subtotal_bs", "iva_bs"]:
            try:
                conn.execute(f"ALTER TABLE ventas ADD COLUMN {col} REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
