from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from .config import config, init_db
from .routers import register_routers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="HR Data Platform",
    description="MVP API for uploading and exploring candidate data from XLSX files, with an optional chat interface for natural-language queries.",
    version="0.2.0",
)


# ---------------------------------------------------------
# Startup event: Initialize database
# ---------------------------------------------------------

@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    init_db()


# ---------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Request logging middleware (for debugging)
# ---------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests for debugging authentication issues."""
    auth_header = request.headers.get("authorization")
    if auth_header:
        # Log only first 30 chars of token for security
        token_preview = auth_header[:30] + "..." if len(auth_header) > 30 else auth_header
        logger.info(f"Request to {request.url.path} - Auth header present: {token_preview}")
    else:
        logger.warning(f"Request to {request.url.path} - No Authorization header")
    
    response = await call_next(request)
    return response


# ---------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------

@app.get("/health", tags=["system"])
def health_check() -> dict:
    """
    Simple health endpoint to verify the API is running.
    """
    return {"status": "ok"}


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

register_routers(app)


# ---------------------------------------------------------
# Run server with python main.py
# ---------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False
    )