"""
main.py
-------
FastAPI application entrypoint.

Run with:
    uv run uvicorn server.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import router
from server.config import settings

app = FastAPI(title="Agentic Tool Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"name": "Agentic Tool Server", "status": "running", "docs": "/docs"}
