from app.routes.health import router as health_router
from app.routes.items import router as items_router
from app.routes.auth import router as auth_router
from app.routes.folders import router as folders_router
from app.routes.files import router as files_router

__all__ = ["health_router", "items_router", "auth_router", "folders_router", "files_router"]
