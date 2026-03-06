from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import (
    Base,
    engine,
    migrate_add_source_sheet_column,
    migrate_add_source_table_index_column,
    migrate_add_expected_salary_text_column,
)
from .routers import candidates, chat, import_xlsx


Base.metadata.create_all(bind=engine)
# Run migrations to add new columns if needed
migrate_add_source_sheet_column()
migrate_add_source_table_index_column()
migrate_add_expected_salary_text_column()

app = FastAPI(
    title="HR Data Platform",
    description=(
        "MVP API for uploading and exploring candidate data from XLSX files, "
        "with an optional chat interface for natural-language queries."
    ),
    version="0.2.0",
)

# Configure CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://localhost:3000",  # Alternative port
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """
    Simple health endpoint to verify the API is running.
    """
    return {"status": "ok"}


app.include_router(import_xlsx.router)
app.include_router(candidates.router)
app.include_router(chat.router)


