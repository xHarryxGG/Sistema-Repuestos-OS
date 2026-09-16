from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.database import get_db
from app.dependencies import template_context
from app.templating import templates

router = APIRouter(prefix="/cierre", tags=["cierre"])


@router.get("/", response_class=HTMLResponse)
async def cierre_diario(request: Request, fecha: str = ""):
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        cierre = conn.execute(
            "SELECT * FROM cierres_diarios WHERE fecha=?", (fecha,)
        ).fetchone()

        ventas = conn.execute(
            """SELECT v.*, c.nombre as cliente_nombre
               FROM ventas v LEFT JOIN clientes c ON c.id = v.cliente_id
               WHERE date(v.fecha)=? ORDER BY v.fecha""",
            (fecha,),
        ).fetchall()

        resumen = conn.execute(
            """SELECT COUNT(*) as num_ventas,
                      COALESCE(SUM(total_usd),0) as total_usd,
                      COALESCE(SUM(total_bs),0) as total_bs
               FROM ventas WHERE date(fecha)=?""",
            (fecha,),
        ).fetchone()

        pagos = conn.execute(
            """SELECT vp.metodo_pago,
                      COALESCE(SUM(vp.monto_usd),0) as total_usd,
                      COALESCE(SUM(vp.monto_bs),0) as total_bs
               FROM venta_pagos vp JOIN ventas v ON v.id = vp.venta_id
               WHERE date(v.fecha)=? GROUP BY vp.metodo_pago""",
            (fecha,),
        ).fetchall()

        historial = conn.execute(
            "SELECT * FROM cierres_diarios ORDER BY fecha DESC LIMIT 30"
        ).fetchall()

    ctx = template_context(request)
    ctx.update({
        "active": "cierre",
        "fecha": fecha,
        "cierre": dict(cierre) if cierre else None,
        "ventas": [dict(v) for v in ventas],
        "resumen": dict(resumen),
        "pagos": [dict(p) for p in pagos],
        "historial": [dict(h) for h in historial],
    })
    return templates.TemplateResponse("cierre/index.html", ctx)


@router.post("/cerrar")
async def cerrar_dia(fecha: str = Form(...), notas: str = Form("")):
    with get_db() as conn:
        resumen = conn.execute(
            """SELECT COUNT(*) as num_ventas,
                      COALESCE(SUM(total_usd),0) as total_usd,
                      COALESCE(SUM(total_bs),0) as total_bs
               FROM ventas WHERE date(fecha)=?""",
            (fecha,),
        ).fetchone()

        efectivo = conn.execute(
            """SELECT COALESCE(SUM(vp.monto_bs),0) as total
               FROM venta_pagos vp JOIN ventas v ON v.id = vp.venta_id
               WHERE date(v.fecha)=? AND vp.metodo_pago='efectivo'""",
            (fecha,),
        ).fetchone()

        pago_movil = conn.execute(
            """SELECT COALESCE(SUM(vp.monto_bs),0) as total
               FROM venta_pagos vp JOIN ventas v ON v.id = vp.venta_id
               WHERE date(v.fecha)=? AND vp.metodo_pago='pago_movil'""",
            (fecha,),
        ).fetchone()

        punto = conn.execute(
            """SELECT COALESCE(SUM(vp.monto_bs),0) as total
               FROM venta_pagos vp JOIN ventas v ON v.id = vp.venta_id
               WHERE date(v.fecha)=? AND vp.metodo_pago='punto'""",
            (fecha,),
        ).fetchone()

        divisas = conn.execute(
            """SELECT COALESCE(SUM(vp.monto_usd),0) as total
               FROM venta_pagos vp JOIN ventas v ON v.id = vp.venta_id
               WHERE date(v.fecha)=? AND vp.metodo_pago='divisas'""",
            (fecha,),
        ).fetchone()

        conn.execute(
            """INSERT INTO cierres_diarios
               (fecha, total_ventas_usd, total_ventas_bs, total_efectivo_usd,
                total_pago_movil_bs, total_punto_bs, total_divisas_usd, num_ventas, notas)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(fecha) DO UPDATE SET
                total_ventas_usd=excluded.total_ventas_usd,
                total_ventas_bs=excluded.total_ventas_bs,
                total_efectivo_usd=excluded.total_efectivo_usd,
                total_pago_movil_bs=excluded.total_pago_movil_bs,
                total_punto_bs=excluded.total_punto_bs,
                total_divisas_usd=excluded.total_divisas_usd,
                num_ventas=excluded.num_ventas,
                notas=excluded.notas""",
            (
                fecha,
                resumen["total_usd"],
                resumen["total_bs"],
                efectivo["total"],
                pago_movil["total"],
                punto["total"],
                divisas["total"],
                resumen["num_ventas"],
                notas,
            ),
        )

        conn.execute(
            "UPDATE ventas SET cerrada=1 WHERE date(fecha)=?", (fecha,)
        )

    return RedirectResponse(f"/cierre?fecha={fecha}", status_code=303)
