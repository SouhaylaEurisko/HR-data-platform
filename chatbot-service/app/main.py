"""
Chatbot service main application.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config, init_db
from .routers import register_routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    """
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: Add any cleanup code here if needed
    pass


app = FastAPI(
    title="Chatbot Service",
    description="Microservice for LLM-powered chat operations and conversation management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
register_routers(app)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "chatbot"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False
    )
