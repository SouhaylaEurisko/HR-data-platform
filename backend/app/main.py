from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import config, init_db
from .exception_handlers import register_exception_handlers
from .routers import register_routers
from .telemetry import (
    add_inbound_access_middleware,
    reattach_root_log_handlers,
    setup_telemetry,
)
from .prometheus_setup import mount_prometheus_metrics

app = FastAPI(
    title="HR Data Platform",
    version="0.2.0",
)

# Order matters: Starlette prepends each middleware. Last registered = outermost.
# Prometheus + CORS first, then OTel bootstrap, then access log outermost so OPTIONS hit it too.
setup_telemetry(app)
mount_prometheus_metrics(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_inbound_access_middleware(app)


@app.on_event("startup")
def startup_event():
    # Uvicorn applies logging.config after import; restore OTLP handlers for Loki export.
    reattach_root_log_handlers()
    init_db()

register_exception_handlers(app)
register_routers(app)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False,
    )