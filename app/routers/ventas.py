import json
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.database import get_db
from app.dependencies import template_context, METODOS_PAGO
from app.services.bcv import usd_to_bs
from app.services.movimientos import registrar_movimiento
from app.templating import templates

router = APIRouter(prefix="/ventas", tags=["ventas"])


def _registrar_pago(
    conn,
    venta_id: int,
    metodo_pago: str,
    total_usd: float,
    total_bs: float,
    monto_usd: float,
    monto_bs: float,
    cashea_monto_inicial_usd: float = 0,
    cashea_monto_inicial_bs: float = 0,
    cashea_metodo_inicial: str = "pago_movil",
    cashea_monto_cashea_usd: float = 0,
    cashea_monto_cashea_bs: float = 0,
):
    if metodo_pago == "cashea":
        if cashea_monto_inicial_bs > 0 or cashea_monto_inicial_usd > 0:
            metodo_init = cashea_metodo_inicial if cashea_metodo_inicial in METODOS_PAGO else "pago_movil"
            if metodo_init == "divisas":
                conn.execute(
                    "INSERT INTO venta_pagos (venta_id, metodo_pago, monto_usd, monto_bs) VALUES (?,?,?,?)",
                    (venta_id, metodo_init, cashea_monto_inicial_usd, 0),
                )
            else:
                conn.execute(
                    "INSERT INTO venta_pagos (venta_id, metodo_pago, monto_usd, monto_bs) VALUES (?,?,?,?)",
                    (venta_id, metodo_init, 0, cashea_monto_inicial_bs),
                )
        conn.execute(
            "INSERT INTO venta_pagos (venta_id, metodo_pago, monto_usd, monto_bs) VALUES (?,?,?,?)",
            (venta_id, "cashea", cashea_monto_cashea_usd, cashea_monto_cashea_bs),
        )
    elif metodo_pago == "divisas":
        conn.execute(
            "INSERT INTO venta_pagos (venta_id, metodo_pago, monto_usd, monto_bs) VALUES (?,?,?,?)",
            (venta_id, metodo_pago, total_usd, 0),
        )
    else:
        conn.execute(
            "INSERT INTO venta_pagos (venta_id, metodo_pago, monto_usd, monto_bs) VALUES (?,?,?,?)",
            (venta_id, metodo_pago, 0, monto_bs or total_bs),
        )


@router.get("/", response_class=HTMLResponse)
async def listar_ventas(request: Request, fecha: str = ""):
    query = """
        SELECT v.*, c.nombre as cliente_nombre,
               (SELECT GROUP_CONCAT(p.nombre || ' x' || vd.cantidad, ', ')
                FROM venta_detalles vd
                JOIN productos p ON p.id = vd.producto_id
                WHERE vd.venta_id = v.id) as productos
        FROM ventas v LEFT JOIN clientes c ON c.id = v.cliente_id
    """
    params: list = []
    if fecha:
        query += " WHERE date(v.fecha) = ?"
        params.append(fecha)
    query += " ORDER BY v.fecha DESC LIMIT 100"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    ctx = template_context(request)
    ctx.update({"active": "ventas", "ventas": [dict(r) for r in rows], "fecha": fecha})
    return templates.TemplateResponse("ventas/lista.html", ctx)


@router.get("/registrar", response_class=HTMLResponse)
async def registrar_venta(request: Request):
    with get_db() as conn:
        productos = conn.execute(
            "SELECT * FROM productos WHERE activo=1 AND stock > 0 ORDER BY nombre"
        ).fetchall()
        clientes = conn.execute("SELECT * FROM clientes ORDER BY nombre").fetchall()

    ctx = template_context(request)
    ctx.update({
        "active": "registrar",
        "productos": [dict(p) for p in productos],
        "clientes": [dict(c) for c in clientes],
        "metodos_pago": METODOS_PAGO,
    })
    return templates.TemplateResponse("ventas/registrar.html", ctx)


@router.post("/registrar")
async def procesar_venta(
    cliente_id: str = Form(""),
    tasa_cambio: float = Form(...),
    items_json: str = Form(...),
    metodo_pago: str = Form(...),
    monto_usd: float = Form(0),
    monto_bs: float = Form(0),
    cashea_monto_inicial_usd: float = Form(0),
    cashea_monto_inicial_bs: float = Form(0),
    cashea_metodo_inicial: str = Form("pago_movil"),
    cashea_monto_cashea_usd: float = Form(0),
    cashea_monto_cashea_bs: float = Form(0),
    notas: str = Form(""),
):
    items = json.loads(items_json)
    if not items:
        return RedirectResponse("/ventas/registrar", status_code=303)

    total_usd = round(sum(i["cantidad"] * i["precio_usd"] for i in items), 2)
    total_bs = usd_to_bs(total_usd, tasa_cambio)

    subtotal_usd = round(total_usd / 1.16, 2)
    iva_usd = round(total_usd - subtotal_usd, 2)

    subtotal_bs = round(total_bs / 1.16, 2)
    iva_bs = round(total_bs - subtotal_bs, 2)

    cid = int(cliente_id) if cliente_id else None

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO ventas (cliente_id, total_usd, total_bs, subtotal_usd, iva_usd, subtotal_bs, iva_bs, tasa_cambio, notas)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (cid, total_usd, total_bs, subtotal_usd, iva_usd, subtotal_bs, iva_bs, tasa_cambio, notas),
        )
        venta_id = cur.lastrowid
        productos_vendidos = []

        for item in items:
            subtotal = item["cantidad"] * item["precio_usd"]
            prod = conn.execute("SELECT nombre FROM productos WHERE id=?", (item["producto_id"],)).fetchone()
            nombre = prod["nombre"] if prod else f"ID {item['producto_id']}"
            productos_vendidos.append(f"{nombre} x{item['cantidad']}")

            conn.execute(
                """INSERT INTO venta_detalles (venta_id, producto_id, cantidad, precio_unitario_usd, subtotal_usd)
                   VALUES (?,?,?,?,?)""",
                (venta_id, item["producto_id"], item["cantidad"], item["precio_usd"], subtotal),
            )
            conn.execute(
                "UPDATE productos SET stock = stock - ? WHERE id = ?",
                (item["cantidad"], item["producto_id"]),
            )

        _registrar_pago(
            conn,
            venta_id,
            metodo_pago,
            total_usd,
            total_bs,
            monto_usd,
            monto_bs,
            cashea_monto_inicial_usd,
            cashea_monto_inicial_bs,
            cashea_metodo_inicial,
            cashea_monto_cashea_usd,
            cashea_monto_cashea_bs,
        )

        registrar_movimiento(
            conn, "venta", venta_id, "crear",
            f"Venta #{venta_id} registrada: {', '.join(productos_vendidos)} — ${total_usd:.2f}",
            datos_nuevos={"productos": productos_vendidos, "total_usd": total_usd, "metodo_pago": metodo_pago},
        )

    return RedirectResponse(f"/ventas/{venta_id}", status_code=303)


@router.get("/{venta_id}", response_class=HTMLResponse)
async def detalle_venta(request: Request, venta_id: int):
    with get_db() as conn:
        venta = conn.execute(
            """SELECT v.*, c.nombre as cliente_nombre, c.telefono as cliente_telefono
               FROM ventas v LEFT JOIN clientes c ON c.id = v.cliente_id WHERE v.id=?""",
            (venta_id,),
        ).fetchone()
        if not venta:
            return RedirectResponse("/ventas", status_code=303)

        vdict = dict(venta)
        if not vdict.get("subtotal_bs") or vdict["subtotal_bs"] == 0:
            vdict["subtotal_bs"] = round(vdict["total_bs"] / 1.16, 2)
            vdict["iva_bs"] = round(vdict["total_bs"] - vdict["subtotal_bs"], 2)
            vdict["subtotal_usd"] = round(vdict["total_usd"] / 1.16, 2)
            vdict["iva_usd"] = round(vdict["total_usd"] - vdict["subtotal_usd"], 2)

        detalles = conn.execute(
            """SELECT vd.*, p.nombre as producto_nombre, p.codigo
               FROM venta_detalles vd JOIN productos p ON p.id = vd.producto_id
               WHERE vd.venta_id=?""",
            (venta_id,),
        ).fetchall()
        pagos = conn.execute(
            "SELECT * FROM venta_pagos WHERE venta_id=?", (venta_id,)
        ).fetchall()

    ctx = template_context(request)
    ctx.update({
        "active": "ventas",
        "venta": vdict,
        "detalles": [dict(d) for d in detalles],
        "pagos": [dict(p) for p in pagos],
    })
    return templates.TemplateResponse("ventas/detalle.html", ctx)
    return templates.TemplateResponse("ventas/detalle.html", ctx)


@router.post("/{venta_id}/eliminar")
async def eliminar_venta(venta_id: int):
    with get_db() as conn:
        venta = conn.execute("SELECT * FROM ventas WHERE id=?", (venta_id,)).fetchone()
        if not venta:
            return RedirectResponse("/ventas", status_code=303)

        detalles = conn.execute(
            """SELECT vd.*, p.nombre as producto_nombre
               FROM venta_detalles vd JOIN productos p ON p.id = vd.producto_id
               WHERE vd.venta_id=?""",
            (venta_id,),
        ).fetchall()

        for d in detalles:
            conn.execute(
                "UPDATE productos SET stock = stock + ? WHERE id = ?",
                (d["cantidad"], d["producto_id"]),
            )

        productos_txt = ", ".join(f"{d['producto_nombre']} x{d['cantidad']}" for d in detalles)
        registrar_movimiento(
            conn, "venta", venta_id, "eliminar",
            f"Venta #{venta_id} eliminada. Stock devuelto: {productos_txt}",
            datos_anteriores=dict(venta),
        )
        conn.execute("DELETE FROM ventas WHERE id=?", (venta_id,))

    return RedirectResponse("/ventas", status_code=303)


@router.get("/api/productos")
async def api_productos(q: str = ""):
    with get_db() as conn:
        if q:
            rows = conn.execute(
                """SELECT id, codigo, nombre, precio_usd, stock FROM productos
                   WHERE activo=1 AND stock > 0 AND (nombre LIKE ? OR codigo LIKE ?)
                   LIMIT 20""",
                (f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, codigo, nombre, precio_usd, stock FROM productos WHERE activo=1 AND stock > 0"
            ).fetchall()
    return JSONResponse([dict(r) for r in rows])
