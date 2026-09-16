import os
import sqlite3
from datetime import datetime, date
from contextlib import contextmanager
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = Path(__file__).parent.parent / "data" / "inventario.db"


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or os.environ.get("POSTGRES_URL") or ""
    return url.strip().strip("'").strip('"')


def is_postgres() -> bool:
    url = get_database_url().lower()
    return "postgres://" in url or "postgresql://" in url or "postgres:" in url or "postgresql:" in url


def _format_pg_row(row):
    if not row:
        return row
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v.strftime("%Y-%m-%d")
    return d


class PostgresCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, query: str, params: tuple | list = ()):
        pg_query = query.replace("?", "%s")
        upper_q = pg_query.strip().upper()
        is_insert = upper_q.startswith("INSERT INTO")
        has_returning = "RETURNING" in upper_q

        if is_insert and not has_returning and "ON CONFLICT" not in upper_q and "INTO CONFIGURACION" not in upper_q:
            pg_query = pg_query.rstrip("; ") + " RETURNING id;"

        self._cursor.execute(pg_query, params or ())

        if is_insert and "RETURNING" in pg_query.upper():
            try:
                row = self._cursor.fetchone()
                if row and "id" in row:
                    self.lastrowid = row["id"]
            except Exception:
                pass
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return _format_pg_row(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [_format_pg_row(r) for r in rows] if rows else []


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
    db_url = get_database_url()
    if is_postgres():
        import psycopg2
        url = db_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        try:
            if "sslmode" not in url.lower():
                conn = psycopg2.connect(url, sslmode="require", connect_timeout=10)
            else:
                conn = psycopg2.connect(url, connect_timeout=10)
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            print("PostgreSQL Connection Error:", e)
            if os.environ.get("VERCEL"):
                tmp_db = Path("/tmp") / "inventario.db"
                conn = sqlite3.connect(str(tmp_db), check_same_thread=False)
                conn.row_factory = sqlite3.Row
                return conn
            raise e
    else:
        if os.environ.get("VERCEL"):
            tmp_db = Path("/tmp") / "inventario.db"
            conn = sqlite3.connect(str(tmp_db), check_same_thread=False)
        else:
            try:
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)

        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
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
        try:
            sql_statements = [
                """CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    cedula VARCHAR(50),
                    telefono VARCHAR(50),
                    email VARCHAR(255),
                    direccion TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS productos (
                    id SERIAL PRIMARY KEY,
                    codigo VARCHAR(100) UNIQUE,
                    nombre VARCHAR(255) NOT NULL,
                    descripcion TEXT,
                    categoria VARCHAR(100),
                    precio_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    costo_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    stock INT NOT NULL DEFAULT 0,
                    stock_minimo INT DEFAULT 5,
                    activo INT DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS ventas (
                    id SERIAL PRIMARY KEY,
                    cliente_id INT REFERENCES clientes(id) ON DELETE SET NULL,
                    total_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    total_bs NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    subtotal_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    iva_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    subtotal_bs NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    iva_bs NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    tasa_cambio NUMERIC(12, 2) NOT NULL DEFAULT 1,
                    notas TEXT,
                    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    cerrada INT DEFAULT 0
                )""",
                """CREATE TABLE IF NOT EXISTS venta_detalles (
                    id SERIAL PRIMARY KEY,
                    venta_id INT NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                    producto_id INT NOT NULL REFERENCES productos(id),
                    cantidad INT NOT NULL,
                    precio_unitario_usd NUMERIC(12, 2) NOT NULL,
                    subtotal_usd NUMERIC(12, 2) NOT NULL
                )""",
                """CREATE TABLE IF NOT EXISTS venta_pagos (
                    id SERIAL PRIMARY KEY,
                    venta_id INT NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                    metodo_pago VARCHAR(50) NOT NULL,
                    monto_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    monto_bs NUMERIC(12, 2) NOT NULL DEFAULT 0
                )""",
                """CREATE TABLE IF NOT EXISTS compras (
                    id SERIAL PRIMARY KEY,
                    proveedor VARCHAR(255),
                    total_usd NUMERIC(12, 2) NOT NULL DEFAULT 0,
                    notas TEXT,
                    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS compra_detalles (
                    id SERIAL PRIMARY KEY,
                    compra_id INT NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
                    producto_id INT NOT NULL REFERENCES productos(id),
                    cantidad INT NOT NULL,
                    precio_unitario_usd NUMERIC(12, 2) NOT NULL,
                    subtotal_usd NUMERIC(12, 2) NOT NULL
                )""",
                """CREATE TABLE IF NOT EXISTS cierres_diarios (
                    id SERIAL PRIMARY KEY,
                    fecha DATE NOT NULL UNIQUE,
                    total_ventas_usd NUMERIC(12, 2) DEFAULT 0,
                    total_ventas_bs NUMERIC(12, 2) DEFAULT 0,
                    total_efectivo_usd NUMERIC(12, 2) DEFAULT 0,
                    total_pago_movil_bs NUMERIC(12, 2) DEFAULT 0,
                    total_punto_bs NUMERIC(12, 2) DEFAULT 0,
                    total_divisas_usd NUMERIC(12, 2) DEFAULT 0,
                    num_ventas INT DEFAULT 0,
                    notas TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS configuracion (
                    clave VARCHAR(100) PRIMARY KEY,
                    valor TEXT NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )""",
                "INSERT INTO configuracion (clave, valor) VALUES ('tasa_cambio', '36.50') ON CONFLICT (clave) DO NOTHING",
                "INSERT INTO configuracion (clave, valor) VALUES ('nombre_negocio', 'Mi Negocio') ON CONFLICT (clave) DO NOTHING",
                """CREATE TABLE IF NOT EXISTS movimientos (
                    id SERIAL PRIMARY KEY,
                    entidad VARCHAR(50) NOT NULL,
                    entidad_id INT NOT NULL,
                    accion VARCHAR(50) NOT NULL,
                    descripcion TEXT NOT NULL,
                    datos_anteriores TEXT,
                    datos_nuevos TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )"""
            ]
            for stmt in sql_statements:
                try:
                    with get_db() as conn:
                        conn.execute(stmt)
                except Exception as stmt_err:
                    print("PG init stmt error:", stmt_err)
        except Exception as e:
            print(f"Warning: PostgreSQL init_db error: {e}")
        return

    try:
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

            for col in ["subtotal_usd", "iva_usd", "subtotal_bs", "iva_bs"]:
                try:
                    conn.execute(f"ALTER TABLE ventas ADD COLUMN {col} REAL DEFAULT 0")
                except sqlite3.OperationalError:
                    pass
    except Exception as e:
        print(f"Warning: init_db encountered an exception: {e}")
