from typing import Optional
import httpx
from bs4 import BeautifulSoup
from app.database import get_db

BCV_URL = "https://www.bcv.org.ve/"


import time

_tasa_cache = None
_tasa_cache_time = 0


def get_tasa_local() -> float:
    global _tasa_cache, _tasa_cache_time
    now = time.time()
    if _tasa_cache is not None and (now - _tasa_cache_time < 60):
        return _tasa_cache
    with get_db() as conn:
        row = conn.execute(
            "SELECT valor FROM configuracion WHERE clave = 'tasa_cambio'"
        ).fetchone()
        val = round(float(row["valor"]), 2) if row else 36.50
        _tasa_cache = val
        _tasa_cache_time = now
        return val


def set_tasa_local(tasa: float) -> float:
    global _tasa_cache, _tasa_cache_time
    tasa = round(tasa, 2)
    with get_db() as conn:
        conn.execute(
            "UPDATE configuracion SET valor = ?, updated_at = CURRENT_TIMESTAMP WHERE clave = 'tasa_cambio'",
            (str(tasa),),
        )
    _tasa_cache = tasa
    _tasa_cache_time = time.time()
    try:
        from app.dependencies import invalidate_config_cache
        invalidate_config_cache()
    except Exception:
        pass
    return tasa



async def fetch_tasa_bcv() -> dict:
    """Obtiene la tasa oficial USD del Banco Central de Venezuela."""
    try:
        async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
            response = await client.get(
                BCV_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        usd_div = soup.find("div", id="dolar")
        if not usd_div:
            raise ValueError("No se encontró el elemento de tasa USD en la página del BCV")

        strong = usd_div.find("strong")
        if not strong:
            raise ValueError("No se pudo extraer el valor de la tasa")

        tasa_str = strong.get_text(strip=True).replace(".", "").replace(",", ".")
        tasa = round(float(tasa_str), 2)
        set_tasa_local(tasa)

        fecha_div = soup.find("span", class_="date-display-single")
        fecha = fecha_div.get_text(strip=True) if fecha_div else None

        return {
            "success": True,
            "tasa": tasa,
            "fecha": fecha,
            "fuente": "BCV",
        }
    except Exception as e:
        tasa_local = round(get_tasa_local(), 2)
        return {
            "success": False,
            "tasa": tasa_local,
            "error": str(e),
            "fuente": "local",
        }


def usd_to_bs(monto_usd: float, tasa: Optional[float] = None) -> float:
    if tasa is None:
        tasa = get_tasa_local()
    return round(monto_usd * tasa, 2)
