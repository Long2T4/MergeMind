"""Call install_stage12(app) after other routers are included."""
from app.stage12.routes import router
from app.stage12.middleware import Stage12AuthMiddleware
from app.stage12.security import install_ownership_filters


def install_stage12(app):
    install_ownership_filters()
    app.include_router(router)
    # Important: add CORS middleware AFTER this middleware if supporting
    # anonymous CORS preflight across all browsers (installer checks ordering).
    app.add_middleware(Stage12AuthMiddleware)
