from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.dependencies import template_context
from app.services.reportes import (
    reporte_ventas,
    reporte_ganancias,
    productos_mas_vendidos,
    productos_bajo_stock,
    ventas_por_dia,
    get_rango_fechas,
    anios_disponibles,
)
from app.templating import templates

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def reportes(
    request: Request,
    tipo: str = "mensual",
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    semana: Optional[int] = None,
    dia: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    fecha_inicio, fecha_fin, etiqueta = get_rango_fechas(
        tipo, anio, mes, semana, dia, fecha_desde, fecha_hasta
    )
    now = datetime.now()

    ctx = template_context(request)
    ctx.update({
        "active": "reportes",
        "tipo": tipo,
        "anio": anio or now.year,
        "mes": mes or now.month,
        "semana": semana or now.isocalendar()[1],
        "dia": dia or now.strftime("%Y-%m-%d"),
        "fecha_desde": fecha_desde or fecha_inicio,
        "fecha_hasta": fecha_hasta or fecha_fin,
        "etiqueta": etiqueta,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "anios": anios_disponibles(),
        "ventas": reporte_ventas(fecha_inicio, fecha_fin),
        "ganancias": reporte_ganancias(fecha_inicio, fecha_fin),
        "mas_vendidos": productos_mas_vendidos(10, fecha_inicio, fecha_fin),
        "bajo_stock": productos_bajo_stock(),
        "ventas_diarias": ventas_por_dia(fecha_inicio, fecha_fin),
    })
    return templates.TemplateResponse("reportes/index.html", ctx)
