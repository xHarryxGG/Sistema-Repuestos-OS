from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.dependencies import template_context
from app.services.movimientos import listar_movimientos, ENTIDADES, ACCIONES
from app.templating import templates

router = APIRouter(prefix="/movimientos", tags=["movimientos"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def listar(request: Request, entidad: str = "", accion: str = ""):
    movimientos = listar_movimientos(entidad=entidad, accion=accion)
    ctx = template_context(request)
    ctx.update({
        "active": "movimientos",
        "movimientos": movimientos,
        "entidad_filter": entidad,
        "accion_filter": accion,
        "entidades": ENTIDADES,
        "acciones": ACCIONES,
    })
    return templates.TemplateResponse("movimientos/index.html", ctx)
