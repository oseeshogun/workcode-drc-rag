import json
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import agent

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    responses={404: {"description": "Item not found"}},
)


def _sse_event(data: Dict[str, Any], event: Optional[str] = None) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    if event:
        return f"event: {event}\ndata: {payload}\n\n"
    return f"data: {payload}\nevent: \n\n"


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


@router.post("/chat/stream")
async def chat_stream(request: Request, body: Annotated[ChatBody, Body()]):
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
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
