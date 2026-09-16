from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from app.database import get_db
from app.services.bcv import fetch_tasa_bcv, get_tasa_local, set_tasa_local

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/tasa-bcv")
async def obtener_tasa_bcv():
    result = await fetch_tasa_bcv()
    return JSONResponse(result)


@router.get("/tasa")
async def obtener_tasa_local():
    return JSONResponse({"tasa": get_tasa_local()})


@router.post("/tasa")
async def actualizar_tasa(tasa: float = Form(...)):
    tasa = set_tasa_local(tasa)
    return JSONResponse({"success": True, "tasa": tasa})


@router.get("/productos/verificar-codigo")
async def verificar_codigo_producto(codigo: str = "", exclude_id: int = 0):
    codigo_clean = codigo.strip()
    if not codigo_clean:
        return JSONResponse({"existe": False})
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, nombre FROM productos WHERE LOWER(codigo) = LOWER(?) AND id != ?",
            (codigo_clean, exclude_id),
        ).fetchone()
        if row:
            return JSONResponse({"existe": True, "nombre": row["nombre"]})
        return JSONResponse({"existe": False})
