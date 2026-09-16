from fastapi import Request
from app.services.bcv import get_tasa_local
from app.database import get_db


def get_config(clave: str, default: str = "") -> str:
    with get_db() as conn:
        row = conn.execute(
            "SELECT valor FROM configuracion WHERE clave = ?", (clave,)
        ).fetchone()
        return row["valor"] if row else default


METODOS_PAGO = {
    "pago_movil": "Pago Móvil",
    "punto": "Punto de Venta",
    "efectivo": "Efectivo",
    "divisas": "Divisas (USD)",
    "biopago": "Biopago",
    "cashea": "Cashea",
}


def template_context(request: Request) -> dict:
    return {
        "request": request,
        "tasa_cambio": get_tasa_local(),
        "nombre_negocio": get_config("nombre_negocio", "Mi Negocio"),
        "metodos_pago": METODOS_PAGO,
    }
