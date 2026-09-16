import json
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.database import get_db
from app.dependencies import template_context
from app.templating import templates

router = APIRouter(prefix="/compras", tags=["compras"])


@router.get("/", response_class=HTMLResponse)
async def listar_compras(request: Request):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM compras ORDER BY fecha DESC LIMIT 50"
        ).fetchall()

    ctx = template_context(request)
    ctx.update({"active": "compras", "compras": [dict(r) for r in rows]})
    return templates.TemplateResponse("compras/lista.html", ctx)


@router.get("/registrar", response_class=HTMLResponse)
async def registrar_compra(request: Request):
    with get_db() as conn:
        productos = conn.execute(
            "SELECT * FROM productos WHERE activo=1 ORDER BY nombre"
        ).fetchall()

    ctx = template_context(request)
    ctx.update({
        "active": "compras",
        "productos": [dict(p) for p in productos],
    })
    return templates.TemplateResponse("compras/registrar.html", ctx)


@router.post("/registrar")
async def procesar_compra(
    proveedor: str = Form(""),
    items_json: str = Form(...),
    notas: str = Form(""),
):
    items = json.loads(items_json)
    if not items:
        return RedirectResponse("/compras/registrar", status_code=303)

    total_usd = sum(i["cantidad"] * i["precio_usd"] for i in items)

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO compras (proveedor, total_usd, notas) VALUES (?,?,?)",
            (proveedor, total_usd, notas),
        )
        compra_id = cur.lastrowid

        for item in items:
            subtotal = item["cantidad"] * item["precio_usd"]
            conn.execute(
                """INSERT INTO compra_detalles (compra_id, producto_id, cantidad, precio_unitario_usd, subtotal_usd)
                   VALUES (?,?,?,?,?)""",
                (compra_id, item["producto_id"], item["cantidad"], item["precio_usd"], subtotal),
            )
            conn.execute(
                "UPDATE productos SET stock = stock + ?, costo_usd = ? WHERE id = ?",
                (item["cantidad"], item["precio_usd"], item["producto_id"]),
            )

    return RedirectResponse("/compras", status_code=303)
