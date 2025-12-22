from functools import lru_cache

from fastapi import FastAPI

from agent.model import model

from .config import Settings
from .routers import agent


@lru_cache(maxsize=1)
def get_settings():
    return Settings()


@lru_cache(maxsize=1)
def get_model():
    return model


app = FastAPI()


@app.get("/health")
def read_health():
    return {"status": "ok"}


app.include_router(agent.router)
