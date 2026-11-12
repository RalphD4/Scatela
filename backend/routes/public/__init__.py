from backend.routes.public.auth_routes import auth_web
from backend.routes.public.child_routes import child_web
from backend.routes.public.guardian_routes import guardian_web

__all__ = ["auth_web", "guardian_web", "child_web"]
