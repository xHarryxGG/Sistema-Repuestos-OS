from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import dashboard, clientes, productos, ventas, compras, cierre, reportes, api, movimientos


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        print("Warning: lifespan init_db non-fatal error:", e)
    yield


app = FastAPI(
    title="Gestión de Inventario",
    description="Sistema de inventario y ventas",
    lifespan=lifespan,
)

static_dir = Path(__file__).parent / "static"
try:
    static_dir.mkdir(exist_ok=True)
except Exception:
    pass

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(dashboard.router)
app.include_router(clientes.router)
app.include_router(productos.router)
app.include_router(ventas.router)
app.include_router(compras.router)
app.include_router(cierre.router)
app.include_router(reportes.router)
app.include_router(movimientos.router)
app.include_router(api.router)
