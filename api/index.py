import sys
from pathlib import Path

# Agregar la raíz del proyecto al sys.path para Vercel Serverless Functions
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.main import app  # noqa: F401
