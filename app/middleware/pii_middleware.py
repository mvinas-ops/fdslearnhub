import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json

from app.roles import ROLE_CONFIG
from app.deps import get_current_user  # your existing deps

# PII patterns
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b\d{9,15}\b"),
    "tin": re.compile(r"\b\d{9,12}\b"),
    # Name detection (basic pattern)
    "firstname": re.compile(r"\b[A-Z][a-z]{1,30}\b"),
    "middlename": re.compile(r"\b[A-Z][a-z]{1,30}\b"),
    "lastname": re.compile(r"\b[A-Z][a-z]{1,30}\b"),
    "extname": re.compile(r"\b[A-Z][a-z]{1,30}\b")
}


class AutoPIIMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Only process JSON
        if "application/json" not in response.headers.get("content-type", ""):
            return response

        # Read the response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        if not body:
            return response

        try:
            data = json.loads(body)
        except Exception:
            return response

        # Get the user from your synchronous get_current_user
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return JSONResponse(content=data)
        try:
            token = auth_header.split(" ")[1]
            user = get_current_user(credentials=type("obj", (), {"credentials": token})())
        except Exception:
            return JSONResponse(content=data)

        role = user.get("role")
        role_data = ROLE_CONFIG.get(role)

        # Mask PII recursively if required
        if role_data and role_data.get("mask_pii"):
            data = self.mask_pii_recursive(data)

        return JSONResponse(content=data, status_code=response.status_code)

    def mask_pii_recursive(self, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    for pattern in PII_PATTERNS.values():
                        if pattern.search(v):
                            obj[k] = "****"
                            break
                elif isinstance(v, (dict, list)):
                    obj[k] = self.mask_pii_recursive(v)
        elif isinstance(obj, list):
            return [self.mask_pii_recursive(item) for item in obj]
        return obj

class ResponseWrapperMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        if "application/json" in response.headers.get("content-type", ""):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            try:
                data = json.loads(body)

                # Skip if already formatted
                if isinstance(data, dict) and "status" in data:
                    return JSONResponse(content=data, status_code=response.status_code)

                return JSONResponse(
                    content={
                        "status": "success",
                        "message": "Success",
                        "data": data,
                        "meta": None
                    },
                    status_code=response.status_code
                )
            except:
                pass