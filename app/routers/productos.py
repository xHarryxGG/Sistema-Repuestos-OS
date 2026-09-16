from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.database import get_db
from app.dependencies import template_context
from app.services.movimientos import registrar_movimiento
from app.templating import templates

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("/", response_class=HTMLResponse)
async def listar_productos(request: Request, q: str = "", categoria: str = ""):
    query = "SELECT * FROM productos WHERE activo=1"
    params: list = []
    if q:
        query += " AND (nombre LIKE ? OR codigo LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    query += " ORDER BY nombre"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        categorias = conn.execute(
            "SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL AND categoria != ''"
        ).fetchall()

    ctx = template_context(request)
    ctx.update({
        "active": "productos",
        "productos": [dict(r) for r in rows],
        "categorias": [r["categoria"] for r in categorias],
        "q": q,
        "categoria_filter": categoria,
    })
    return templates.TemplateResponse("productos/lista.html", ctx)


@router.get("/nuevo", response_class=HTMLResponse)
async def nuevo_producto(request: Request):
    ctx = template_context(request)
    ctx.update({"active": "productos", "producto": None})
    return templates.TemplateResponse("productos/form.html", ctx)


@router.post("/nuevo")
async def crear_producto(
    request: Request,
    nombre: str = Form(...),
    codigo: str = Form(""),
    descripcion: str = Form(""),
    categoria: str = Form(""),
    precio_usd: float = Form(...),
    costo_usd: float = Form(0),
    stock: int = Form(0),
    stock_minimo: int = Form(5),
):
    codigo_clean = codigo.strip() if codigo and codigo.strip() else None
    if codigo_clean:
        with get_db() as conn:
            existente = conn.execute(
                "SELECT id, nombre FROM productos WHERE LOWER(codigo) = LOWER(?)",
                (codigo_clean,),
            ).fetchone()
            if existente:
                ctx = template_context(request)
                ctx.update({
                    "active": "productos",
                    "error": f"El código '{codigo_clean}' ya pertenece al producto '{existente['nombre']}'.",
                    "producto": {
                        "nombre": nombre,
                        "codigo": codigo,
                        "descripcion": descripcion,
                        "categoria": categoria,
                        "precio_usd": precio_usd,
                        "costo_usd": costo_usd,
                        "stock": stock,
                        "stock_minimo": stock_minimo,
                    },
                })
                return templates.TemplateResponse("productos/form.html", ctx, status_code=400)

    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO productos (nombre, codigo, descripcion, categoria, precio_usd, costo_usd, stock, stock_minimo)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (nombre, codigo_clean, descripcion, categoria, precio_usd, costo_usd, stock, stock_minimo),
            )
        return RedirectResponse("/productos", status_code=303)
    except Exception as e:
        ctx = template_context(request)
        ctx.update({
            "active": "productos",
            "error": "El código ingresado ya existe o ocurrió un error al guardar.",
            "producto": {
                "nombre": nombre,
                "codigo": codigo,
                "descripcion": descripcion,
                "categoria": categoria,
                "precio_usd": precio_usd,
                "costo_usd": costo_usd,
                "stock": stock,
                "stock_minimo": stock_minimo,
            },
        })
        return templates.TemplateResponse("productos/form.html", ctx, status_code=400)


@router.get("/{producto_id}/editar", response_class=HTMLResponse)
async def editar_producto(request: Request, producto_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
    if not row:
        return RedirectResponse("/productos", status_code=303)
    ctx = template_context(request)
    ctx.update({"active": "productos", "producto": dict(row)})
    return templates.TemplateResponse("productos/form.html", ctx)


@router.post("/{producto_id}/editar")
async def actualizar_producto(
    request: Request,
    producto_id: int,
    nombre: str = Form(...),
    codigo: str = Form(""),
    descripcion: str = Form(""),
    categoria: str = Form(""),
    precio_usd: float = Form(...),
    costo_usd: float = Form(0),
    stock: int = Form(0),
    stock_minimo: int = Form(5),
):
    codigo_clean = codigo.strip() if codigo and codigo.strip() else None
    if codigo_clean:
        with get_db() as conn:
            existente = conn.execute(
                "SELECT id, nombre FROM productos WHERE LOWER(codigo) = LOWER(?) AND id != ?",
                (codigo_clean, producto_id),
            ).fetchone()
            if existente:
                ctx = template_context(request)
                ctx.update({
                    "active": "productos",
                    "error": f"El código '{codigo_clean}' ya pertenece al producto '{existente['nombre']}'.",
                    "producto": {
                        "id": producto_id,
                        "nombre": nombre,
                        "codigo": codigo,
                        "descripcion": descripcion,
                        "categoria": categoria,
                        "precio_usd": precio_usd,
                        "costo_usd": costo_usd,
                        "stock": stock,
                        "stock_minimo": stock_minimo,
                    },
                })
                return templates.TemplateResponse("productos/form.html", ctx, status_code=400)

    try:
        with get_db() as conn:
            anterior = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
            conn.execute(
                """UPDATE productos SET nombre=?, codigo=?, descripcion=?, categoria=?,
                   precio_usd=?, costo_usd=?, stock=?, stock_minimo=? WHERE id=?""",
                (nombre, codigo_clean, descripcion, categoria, precio_usd, costo_usd, stock, stock_minimo, producto_id),
            )
            nuevo = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
            registrar_movimiento(
                conn, "producto", producto_id, "editar",
                f"Producto '{nombre}' editado",
                datos_anteriores=dict(anterior) if anterior else None,
                datos_nuevos=dict(nuevo) if nuevo else None,
            )
        return RedirectResponse("/productos", status_code=303)
    except Exception as e:
        ctx = template_context(request)
        ctx.update({
            "active": "productos",
            "error": "No se pudo actualizar el producto. Verifique que el código no esté duplicado.",
            "producto": {
                "id": producto_id,
                "nombre": nombre,
                "codigo": codigo,
                "descripcion": descripcion,
                "categoria": categoria,
                "precio_usd": precio_usd,
                "costo_usd": costo_usd,
                "stock": stock,
                "stock_minimo": stock_minimo,
            },
        })
        return templates.TemplateResponse("productos/form.html", ctx, status_code=400)


@router.post("/{producto_id}/eliminar")
async def eliminar_producto(producto_id: int):
    with get_db() as conn:
        producto = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
        if producto:
            registrar_movimiento(
                conn, "producto", producto_id, "eliminar",
                f"Producto '{producto['nombre']}' desactivado",
                datos_anteriores=dict(producto),
            )
            conn.execute("UPDATE productos SET activo=0 WHERE id=?", (producto_id,))
    return RedirectResponse("/productos", status_code=303)
