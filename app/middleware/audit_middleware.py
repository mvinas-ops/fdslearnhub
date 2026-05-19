from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import json
from app.auth import get_user_from_token   # ✅ no dot
from app.logger import logger              # ✅ no dot

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # ✅ read body safely
        body = await request.body()
        request._body = body

        try:
            request_data = json.loads(body.decode())
        except:
            request_data = None

        response = await call_next(request)

        # ✅ extract user from JWT
        auth_header = request.headers.get("Authorization")
        user = "anonymous"

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            user = get_user_from_token(token)

        # ❌ remove sensitive fields
        if isinstance(request_data, dict):
            request_data.pop("password", None)

        log = {
            "user": user,
            "method": request.method,
            "endpoint": request.url.path,
            "status": response.status_code,
            "ip": request.client.host,
            "body": request_data
        }

        logger.info(json.dumps(log))

        return response