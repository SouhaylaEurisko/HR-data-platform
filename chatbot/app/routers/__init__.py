"""
Routers package for chatbot service.
"""
from fastapi import FastAPI

from . import conversations, messages


def register_routers(app: FastAPI) -> None:
    """
    Register all routers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.include_router(conversations.router)
    app.include_router(messages.router)
