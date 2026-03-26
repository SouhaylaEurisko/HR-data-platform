"""
Routers package - registers all API routers with the FastAPI app.
"""
from fastapi import FastAPI

from . import analytics, candidates, import_xlsx, auth, chatbot_gateway, lookups, custom_fields, resume


def register_routers(app: FastAPI) -> None:
    app.include_router(auth.router)
    app.include_router(analytics.router)
    app.include_router(candidates.router)
    app.include_router(import_xlsx.router)
    app.include_router(chatbot_gateway.router)
    app.include_router(lookups.router)
    app.include_router(custom_fields.router)
    app.include_router(resume.router)
