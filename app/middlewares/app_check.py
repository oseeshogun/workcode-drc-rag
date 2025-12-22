from fastapi import Request
from fastapi.responses import JSONResponse
from firebase_admin.exceptions import FirebaseError

from app import app
from app.services.verify_app_check_token import verify_app_check_token_safe


@app.middleware("http")
async def app_check(request: Request, call_next):
    token = request.headers.get("X-Firebase-AppCheck")
    if not token:
        return JSONResponse(
            status_code=401, content={"error": "Missing App Check token"}
        )
    try:
        decoded_token = verify_app_check_token_safe(token)
    except FirebaseError as e:
        return JSONResponse(status_code=401, content={"error": str(e)})
    if not decoded_token:
        return JSONResponse(
            status_code=401, content={"error": "Invalid App Check token"}
        )
    response = await call_next(request)
    return response
