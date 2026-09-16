import json
from typing import Any, Optional
from app.database import get_db

ENTIDADES = {
    "producto": "Producto",
    "cliente": "Cliente",
    "venta": "Venta",
}

ACCIONES = {
    "crear": "Creación",
    "editar": "Edición",
    "eliminar": "Eliminación",
}


def registrar_movimiento(
    conn,
    entidad: str,
    entidad_id: int,
    accion: str,
    descripcion: str,
    datos_anteriores: Optional[dict] = None,
    datos_nuevos: Optional[dict] = None,
):
    conn.execute(
        """INSERT INTO movimientos (entidad, entidad_id, accion, descripcion, datos_anteriores, datos_nuevos)
           VALUES (?,?,?,?,?,?)""",
        (
            entidad,
            entidad_id,
            accion,
            descripcion,
            json.dumps(datos_anteriores, ensure_ascii=False) if datos_anteriores else None,
            json.dumps(datos_nuevos, ensure_ascii=False) if datos_nuevos else None,
        ),
    )


def listar_movimientos(
    entidad: str = "",
    accion: str = "",
    limit: int = 100,
) -> list:
    query = "SELECT * FROM movimientos WHERE 1=1"
    params: list[Any] = []
    if entidad:
        query += " AND entidad = ?"
        params.append(entidad)
    if accion:
        query += " AND accion = ?"
        params.append(accion)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
