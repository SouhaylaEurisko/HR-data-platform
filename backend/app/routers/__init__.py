"""
Routers package - registers all API routers with the FastAPI app.
"""
from fastapi import FastAPI

from . import candidates, import_xlsx, auth, chatbot_gateway


def register_routers(app: FastAPI) -> None:
    """
    Register all routers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Register auth routes
    app.include_router(auth.router)
    
    # Register candidate routes
    app.include_router(candidates.router)
    
    # Register import routes
    app.include_router(import_xlsx.router)
    
    # Register chatbot gateway routes
    app.include_router(chatbot_gateway.router)