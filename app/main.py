from functools import lru_cache
from typing import Annotated

from fastapi import Body, Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.indexing import index_documents
from agent.model import model
from app.config import Settings

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


class IndexDocumentsRequest(BaseModel):
    password: str = Field(description="Password for indexing.")


@app.post("/indexing")
async def index_documents_api(
    body: Annotated[IndexDocumentsRequest, Body()],
    settings: Annotated[Settings, Depends(get_settings)],
):
    if body.password != settings.indexing_pwd:
        raise HTTPException(status_code=403, detail="Invalid password")
    index_documents()
    return {"message": "Documents indexed successfully"}


app.include_router(agent.router)
