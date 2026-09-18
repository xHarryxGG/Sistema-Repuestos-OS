import time
from fastapi import Request
from app.services.bcv import get_tasa_local
from app.database import get_db

_config_cache = {}
_config_cache_time = 0


def get_config(clave: str, default: str = "") -> str:
    global _config_cache, _config_cache_time
    now = time.time()
    if not _config_cache or (now - _config_cache_time > 60):
        try:
            with get_db() as conn:
                rows = conn.execute("SELECT clave, valor FROM configuracion").fetchall()
                _config_cache = {r["clave"]: r["valor"] for r in rows}
                _config_cache_time = now
        except Exception:
            pass
    return _config_cache.get(clave, default)


def invalidate_config_cache():
    global _config_cache, _config_cache_time
    _config_cache = {}
    _config_cache_time = 0


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
