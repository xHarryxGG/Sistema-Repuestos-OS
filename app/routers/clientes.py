from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.database import get_db
from app.dependencies import template_context
from app.services.movimientos import registrar_movimiento
from app.templating import templates

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("/", response_class=HTMLResponse)
async def listar_clientes(request: Request, q: str = ""):
    with get_db() as conn:
        if q:
            rows = conn.execute(
                """SELECT * FROM clientes
                   WHERE nombre LIKE ? OR cedula LIKE ? OR telefono LIKE ?
                   ORDER BY nombre""",
                (f"%{q}%", f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM clientes ORDER BY nombre").fetchall()

    ctx = template_context(request)
    ctx.update({"active": "clientes", "clientes": [dict(r) for r in rows], "q": q})
    return templates.TemplateResponse("clientes/lista.html", ctx)


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_cliente(request: Request):
    ctx = template_context(request)
    ctx.update({"active": "clientes", "cliente": None})
    return templates.TemplateResponse("clientes/form.html", ctx)


@router.post("/nuevo")
async def crear_cliente(
    nombre: str = Form(...),
    cedula: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO clientes (nombre, cedula, telefono, email, direccion) VALUES (?,?,?,?,?)",
            (nombre, cedula, telefono, email, direccion),
        )
    return RedirectResponse("/clientes", status_code=303)


@router.post("/api/crear")
async def crear_cliente_api(
    nombre: str = Form(...),
    cedula: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO clientes (nombre, cedula, telefono, email, direccion) VALUES (?,?,?,?,?)",
            (nombre, cedula, telefono, email, direccion),
        )
        cliente_id = cur.lastrowid
        row = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
    return JSONResponse({"success": True, "cliente": dict(row)})


@router.get("/{cliente_id}/editar", response_class=HTMLResponse)
async def editar_cliente(request: Request, cliente_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
    if not row:
        return RedirectResponse("/clientes", status_code=303)
    ctx = template_context(request)
    ctx.update({"active": "clientes", "cliente": dict(row)})
    return templates.TemplateResponse("clientes/form.html", ctx)


@router.post("/{cliente_id}/editar")
async def actualizar_cliente(
    cliente_id: int,
    nombre: str = Form(...),
    cedula: str = Form(""),
    telefono: str = Form(""),
    email: str = Form(""),
    direccion: str = Form(""),
):
    with get_db() as conn:
        anterior = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        conn.execute(
            """UPDATE clientes SET nombre=?, cedula=?, telefono=?, email=?, direccion=?
               WHERE id=?""",
            (nombre, cedula, telefono, email, direccion, cliente_id),
        )
        nuevo = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        registrar_movimiento(
            conn, "cliente", cliente_id, "editar",
            f"Cliente '{nombre}' editado",
            datos_anteriores=dict(anterior) if anterior else None,
            datos_nuevos=dict(nuevo) if nuevo else None,
        )
    return RedirectResponse("/clientes", status_code=303)


@router.post("/{cliente_id}/eliminar")
async def eliminar_cliente(cliente_id: int):
    with get_db() as conn:
        cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        if cliente:
            registrar_movimiento(
                conn, "cliente", cliente_id, "eliminar",
                f"Cliente '{cliente['nombre']}' eliminado",
                datos_anteriores=dict(cliente),
            )
            conn.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
    return RedirectResponse("/clientes", status_code=303)
