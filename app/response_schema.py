from pydantic import BaseModel
from typing import Any, Optional

class Meta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int

class SuccessResponse(BaseModel):
    status: str = "success"
    message: str
    data: Optional[Any]
    meta: Optional[Meta]
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Data fetched successfully.",
                "data": [
                    {
                        "listahanan_id": "12345",
                        "first_name": "Juan",
                        "last_name": "Dela Cruz"
                    }
                ],
                "meta": {
                    "page": 1,
                    "limit": 10,
                    "total": 100,
                    "total_pages": 10
                },
                "error_code": None
            }
        }


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    data: Optional[Any] = None
    meta: Optional[Any] = None
    error_code: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "Access denied",
                "data": None,
                "meta": None,
                "error_code": "RBAC_FORBIDDEN"
            }
        }