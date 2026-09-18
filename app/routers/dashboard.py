import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.dependencies import template_context
from app.services.reportes import resumen_dashboard, productos_bajo_stock, ventas_por_dia
from app.templating import templates

router = APIRouter()

_dashboard_cache = None
_dashboard_cache_time = 0


def invalidate_dashboard_cache():
    global _dashboard_cache_time
    _dashboard_cache_time = 0


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    global _dashboard_cache, _dashboard_cache_time
    now = time.time()

    if _dashboard_cache is None or (now - _dashboard_cache_time > 15):
        hoy = datetime.now().date()
        inicio = (hoy - timedelta(days=13)).strftime("%Y-%m-%d")
        fin = hoy.strftime("%Y-%m-%d")
        _dashboard_cache = {
            "resumen": resumen_dashboard(),
            "bajo_stock": productos_bajo_stock()[:5],
            "ventas_chart": ventas_por_dia(inicio, fin),
        }
        _dashboard_cache_time = now

    ctx = template_context(request)
    ctx.update({
        "active": "dashboard",
        "resumen": _dashboard_cache["resumen"],
        "bajo_stock": _dashboard_cache["bajo_stock"],
        "ventas_chart": _dashboard_cache["ventas_chart"],
    })
    return templates.TemplateResponse("dashboard.html", ctx)