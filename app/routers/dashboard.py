from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.dependencies import template_context
from app.services.reportes import resumen_dashboard, productos_bajo_stock, ventas_por_dia
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    hoy = datetime.now().date()
    inicio = (hoy - timedelta(days=13)).strftime("%Y-%m-%d")
    fin = hoy.strftime("%Y-%m-%d")

    ctx = template_context(request)
    ctx.update({
        "active": "dashboard",
        "resumen": resumen_dashboard(),
        "bajo_stock": productos_bajo_stock()[:5],
        "ventas_chart": ventas_por_dia(inicio, fin),
    })
    return templates.TemplateResponse("dashboard.html", ctx)