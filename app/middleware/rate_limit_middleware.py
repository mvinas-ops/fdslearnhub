import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 10, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.clients = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()

        if client_ip not in self.clients:
            self.clients[client_ip] = []

        # remove expired timestamps
        self.clients[client_ip] = [
            t for t in self.clients[client_ip]
            if now - t < self.window
        ]

        if len(self.clients[client_ip]) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={
                    "message": "Too many requests",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            )

        self.clients[client_ip].append(now)

        response = await call_next(request)
        return response