from fastapi import APIRouter
from app.response_schema import SuccessResponse, ErrorResponse

class CustomRouter(APIRouter):

    def api_route(self, path: str, **kwargs):

        default_responses = {
            400: {"model": ErrorResponse, "description": "Bad Request"},
            401: {"model": ErrorResponse, "description": "Unauthorized"},
            403: {"model": ErrorResponse, "description": "Forbidden"},
            422: {"model": ErrorResponse, "description": "Validation Error"},
            429: {"model": ErrorResponse, "description": "Rate Limited"},
            500: {"model": ErrorResponse, "description": "Internal Server Error 2"},
            503: {"model": ErrorResponse, "description": "Database Unavailable"},
        }

        def decorator(func):
            user_responses = kwargs.pop("responses", None)

            if isinstance(user_responses, dict):
                default_responses.update(user_responses)

            kwargs["responses"] = default_responses
            kwargs.setdefault("response_model", SuccessResponse)

            # ✅ IMPORTANT: use self, not super()
            return super(CustomRouter, self).api_route(path, **kwargs)(func)

        return decorator