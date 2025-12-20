import json
from enum import Enum
from functools import lru_cache
from typing import Annotated, Any, Dict, List, Optional

from fastapi import Body, FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import agent
from agent.model import model
from config import Settings


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


def _sse_event(data: Dict[str, Any], event: Optional[str] = None) -> str:
    """
    Formats a Server-Sent Events message.

    SSE frame format:
      event: <event>\n
      data: <json>\n
      \n
    """
    payload = json.dumps(data, ensure_ascii=False)
    if event:
        return f"event: {event}\ndata: {payload}\n\n"
    return f"data: {payload}\n\n"


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


@app.post("/chat/stream")
async def chat_stream(request: Request, body: Annotated[ChatBody, Body()]):
    """
    Streams the agent response as SSE.

    SSE events:
      - event: token   data: {"token": "..."}
      - event: done    data: {"status": "done"}
      - event: error   data: {"error": "..."}
    """
    messages = body.messages
    # Agent is imported at module import time (see imports at top of file).

    def event_iter():
        try:
            # `agent.stream()` has a stricter typed input; at runtime it accepts the dict state.
            stream_input: Any = {"messages": [dict(role=message.role, content=message.content) for message in messages]}
            for event in agent.stream(stream_input, stream_mode="values"):
                # `Request.is_disconnected()` is async; this generator is sync (used by `StreamingResponse`),
                # so we can't await it here. If the client disconnects, the server will typically cancel
                # the streaming response; additionally, any write/iteration errors will be caught below.

                # `stream_mode="values"` yields a dict with "messages" list; last message is the latest assistant output
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
        except Exception as e:
            yield _sse_event({"error": str(e)}, event="error")

    return StreamingResponse(
        event_iter(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
