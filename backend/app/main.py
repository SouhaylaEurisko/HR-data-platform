from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import config, init_db
from .routers import register_routers

app = FastAPI(
    title="HR Data Platform",
    version="0.2.0",
)

@app.on_event("startup")
def startup_event():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routers(app)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False,
    )