"""Call install_stage12(app) before adding CORS middleware."""
from app.routes.finding_explanations import router as finding_explanations_router
from app.stage12.routes import router
from app.stage12.middleware import Stage12AuthMiddleware


def install_stage12(app):
    app.include_router(router)
    app.include_router(finding_explanations_router)
    # Add CORS middleware AFTER this one, so CORS stays outermost and browser
    # preflights and error responses keep their CORS headers.
    app.add_middleware(Stage12AuthMiddleware)
