from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from fastapi import Query
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/api/top-up", tags=["TOPUP"])

@router.get("/")
async def list_top_up(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
):

    try:
        offset = (page - 1) * page_size

        sql = text("""
            SELECT * FROM ods_topup_history
            ORDER BY id DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(sql, {"limit": page_size + 1, "offset": offset})
        rows = result.fetchall()

        # Check if next page exists
        has_next = len(rows) > page_size

        # Trim extra row
        rows = rows[:page_size]

        data = [dict(row._mapping) for row in rows]

        msg = "Data fetched successfully." if data else "No record found."

        return {
            "success": True,
            "message": msg,
            "page": page,
            "page_size": page_size,
            "has_next": has_next,
            "data": data
        }

    except Exception as e:

        return {
            "success": False,
            "message": "Server error",
            "error": str(e)
        }

