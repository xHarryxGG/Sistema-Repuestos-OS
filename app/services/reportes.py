import calendar
from datetime import date, datetime, timedelta
from typing import Optional
from app.database import get_db


def get_rango_fechas(
    tipo: str = "mensual",
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    semana: Optional[int] = None,
    dia: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> tuple[str, str, str]:
    """Retorna (fecha_inicio, fecha_fin, etiqueta) según el filtro seleccionado."""
    now = datetime.now()
    anio = anio or now.year

    if tipo == "rango" and fecha_desde and fecha_hasta:
        return fecha_desde, fecha_hasta, f"{fecha_desde} — {fecha_hasta}"

    if tipo == "diario":
        d = dia or now.strftime("%Y-%m-%d")
        return d, d, d

    if tipo == "semanal":
        w = semana or now.isocalendar()[1]
        inicio = date.fromisocalendar(anio, w, 1)
        fin = inicio + timedelta(days=6)
        return inicio.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d"), f"Semana {w} de {anio}"

    if tipo == "mensual":
        m = mes or now.month
        ultimo = calendar.monthrange(anio, m)[1]
        inicio = date(anio, m, 1)
        fin = date(anio, m, ultimo)
        meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        return inicio.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d"), f"{meses[m]} {anio}"

    if tipo == "anual":
        return f"{anio}-01-01", f"{anio}-12-31", str(anio)

    # default mensual actual
    m = now.month
    ultimo = calendar.monthrange(anio, m)[1]
    inicio = date(anio, m, 1)
    fin = date(anio, m, ultimo)
    return inicio.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d"), "Mensual actual"


def _filtro_where(fecha_inicio: str, fecha_fin: str) -> tuple[str, list]:
    return "date(v.fecha) >= ? AND date(v.fecha) <= ?", [fecha_inicio, fecha_fin]


def reporte_ventas(fecha_inicio: str, fecha_fin: str) -> dict:
    where, params = _filtro_where(fecha_inicio, fecha_fin)
    with get_db() as conn:
        ventas = conn.execute(
            f"""
            SELECT COUNT(*) as num_ventas,
                   COALESCE(SUM(total_usd), 0) as total_usd,
                   COALESCE(SUM(total_bs), 0) as total_bs
            FROM ventas v WHERE {where}
            """,
            params,
        ).fetchone()

        pagos = conn.execute(
            f"""
            SELECT vp.metodo_pago,
                   COALESCE(SUM(vp.monto_usd), 0) as total_usd,
                   COALESCE(SUM(vp.monto_bs), 0) as total_bs
            FROM venta_pagos vp
            JOIN ventas v ON v.id = vp.venta_id
            WHERE {where}
            GROUP BY vp.metodo_pago
            """,
            params,
        ).fetchall()

    return {
        "num_ventas": ventas["num_ventas"],
        "total_usd": ventas["total_usd"],
        "total_bs": ventas["total_bs"],
        "pagos_por_metodo": [dict(p) for p in pagos],
    }


def reporte_ganancias(fecha_inicio: str, fecha_fin: str) -> dict:
    where, params = _filtro_where(fecha_inicio, fecha_fin)
    with get_db() as conn:
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM(vd.subtotal_usd), 0) as ingresos_usd,
                   COALESCE(SUM(vd.cantidad * p.costo_usd), 0) as costos_usd
            FROM venta_detalles vd
            JOIN ventas v ON v.id = vd.venta_id
            JOIN productos p ON p.id = vd.producto_id
            WHERE {where}
            """,
            params,
        ).fetchone()

    ingresos = row["ingresos_usd"] or 0
    costos = row["costos_usd"] or 0
    return {
        "ingresos_usd": ingresos,
        "costos_usd": costos,
        "ganancia_usd": ingresos - costos,
        "margen": round(((ingresos - costos) / ingresos * 100) if ingresos > 0 else 0, 2),
    }


def productos_mas_vendidos(limit: int, fecha_inicio: str, fecha_fin: str) -> list:
    where, params = _filtro_where(fecha_inicio, fecha_fin)
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT p.id, p.nombre, p.codigo,
                   SUM(vd.cantidad) as total_vendido,
                   SUM(vd.subtotal_usd) as total_ingresos_usd
            FROM venta_detalles vd
            JOIN ventas v ON v.id = vd.venta_id
            JOIN productos p ON p.id = vd.producto_id
            WHERE {where}
            GROUP BY p.id
            ORDER BY total_vendido DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()
    return [dict(r) for r in rows]


def productos_bajo_stock() -> list:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM productos
            WHERE activo = 1 AND stock <= stock_minimo
            ORDER BY stock ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def ventas_por_dia(fecha_inicio: str, fecha_fin: str) -> list:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT date(fecha) as dia,
                   COUNT(*) as num_ventas,
                   COALESCE(SUM(total_usd), 0) as total_usd
            FROM ventas
            WHERE date(fecha) >= ? AND date(fecha) <= ?
            GROUP BY date(fecha)
            ORDER BY dia ASC
            """,
            (fecha_inicio, fecha_fin),
        ).fetchall()
    return [dict(r) for r in rows]


def anios_disponibles() -> list[int]:
    now = datetime.now().year
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT CAST(strftime('%Y', fecha) AS INTEGER) as anio
            FROM ventas ORDER BY anio DESC
            """
        ).fetchall()
    anios_db = {r["anio"] for r in rows if r["anio"]}
    # Rango amplio para poder seleccionar cualquier año
    anios_rango = set(range(now - 10, now + 2))
    return sorted(anios_db | anios_rango, reverse=True)


def resumen_dashboard() -> dict:
    with get_db() as conn:
        hoy = datetime.now().strftime("%Y-%m-%d")
        ventas_hoy = conn.execute(
            "SELECT COUNT(*) as n, COALESCE(SUM(total_usd),0) as t FROM ventas WHERE date(fecha)=?",
            (hoy,),
        ).fetchone()
        total_clientes = conn.execute("SELECT COUNT(*) as n FROM clientes").fetchone()["n"]
        total_productos = conn.execute(
            "SELECT COUNT(*) as n FROM productos WHERE activo=1"
        ).fetchone()["n"]
        bajo_stock = conn.execute(
            "SELECT COUNT(*) as n FROM productos WHERE activo=1 AND stock <= stock_minimo"
        ).fetchone()["n"]

    inicio, fin, _ = get_rango_fechas("mensual")
    ganancia_mes = reporte_ganancias(inicio, fin)
    return {
        "ventas_hoy": dict(ventas_hoy),
        "total_clientes": total_clientes,
        "total_productos": total_productos,
        "bajo_stock": bajo_stock,
        "ganancia_mes": ganancia_mes,
    }
