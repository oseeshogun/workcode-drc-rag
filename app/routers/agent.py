import json
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import agent
from app.services.verify_app_check_token import verify_app_check_token_safe

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    responses={404: {"description": "Item not found"}},
)


def _sse_event(data: Dict[str, Any], event: Optional[str] = None) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    if event:
        return json.dumps({"event": event, "data": payload})
    return json.dumps({"data": payload})


class UserRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: UserRole = Field(description="Role of the message sender.")
    content: str = Field(description="Content of the message.")


class ChatBody(BaseModel):
    messages: List[ChatMessage] = Field(
        description="List of messages in the conversation.",
        default_factory=list,
        min_length=1,
    )


def _verify_app_check(request: Request) -> None:
    token = request.headers.get("X-Firebase-AppCheck")
    if not token:
        raise HTTPException(status_code=401, detail="Missing App Check token")

    decoded = verify_app_check_token_safe(token)
    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid App Check token")


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    body: Annotated[ChatBody, Body()],
    _: Annotated[None, Depends(_verify_app_check)],
):
    def event_iter():
        stream_input: Any = {
            "messages": [
                dict(role=message.role, content=message.content)
                for message in body.messages
            ]
        }

        for event in agent.stream(stream_input, stream_mode="values"):
            msgs = event.get("messages") if isinstance(event, dict) else None

            if not msgs:
                continue

            last = msgs[-1]
            content = getattr(last, "content", None) or (
                last.get("content") if isinstance(last, dict) else None
            )
            if content:
                yield _sse_event({"token": content}, event="token")

        yield _sse_event({"status": "done"}, event="done")

    return StreamingResponse(
        event_iter(),
        media_type="json/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
