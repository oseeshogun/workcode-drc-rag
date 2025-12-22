import json
import os
from enum import Enum
from functools import lru_cache
from typing import Annotated, Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field

from agent import agent
from agent.model import model
from config import Settings

load_dotenv()

CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", "work-code-service-account.json"
)
SCOPES = ["www.googleapis.com"]


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


@app.post("/verify-integrity")
async def verify_integrity(token_data: dict):
    integrity_token = token_data.get("integrity_token")
    # In a classic request, the nonce should also be sent from the app and validated here
    # For standard requests, Google handles nonce validation using the requestHash.

    if not integrity_token:
        raise HTTPException(status_code=400, detail="Missing integrity token")

    # The package name of your Android app
    package_name = "com.your.app.packagename"

    try:
        # Authenticate and build the Play Integrity API service
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        service = build("playintegrity", "v1", credentials=credentials)

        # The request body for the decode operation
        decode_request_body = {"integrity_token": integrity_token}

        # Call the Google API to decode the token
        request = service.v1().decodeIntegrityToken(
            packageName=package_name, body=decode_request_body
        )
        response = request.execute()

        # Extract the integrity verdict from the response
        verdict = (
            response.get("tokenPayloadExternal", {})
            .get("deviceIntegrity", {})
            .get("deviceRecognitionVerdict", [])
        )

        # Implement your anti-abuse logic
        if "MEETS_DEVICE_INTEGRITY" in verdict:
            # Device is genuine, proceed with sensitive action
            return {
                "status": "success",
                "message": "Integrity check passed",
                "verdict": response,
            }
        else:
            # Device is potentially compromised or an emulator
            return {
                "status": "failure",
                "message": "Device integrity compromised",
                "verdict": response,
            }

    except HttpError as e:
        raise HTTPException(
            status_code=500, detail=f"Google API error: {e.content.decode()}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


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
            stream_input: Any = {
                "messages": [
                    dict(role=message.role, content=message.content)
                    for message in messages
                ]
            }
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
