from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/api/transactional-accounts", tags=["TRANSACTIONAL ACCOUNTS"])

@router.get("/")
async def list_transactional_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    listahanan_id: Optional[str] = Query(None, description="Optional listahanan_id filter"),
):
    try:
        offset = (page - 1) * page_size

        base_sql = """
            SELECT *
            FROM ods_transaction_account
        """

        query_params = {
            "limit": page_size + 1,
            "offset": offset
        }

        if listahanan_id:
            base_sql += " WHERE listahanan_id = :listahanan_id"
            query_params["listahanan_id"] = listahanan_id

        base_sql += " ORDER BY id DESC LIMIT :limit OFFSET :offset"

        sql = text(base_sql)

        result = await db.execute(sql, query_params)
        rows = result.fetchall()

        has_next = len(rows) > page_size
        rows = rows[:page_size]

        data = [dict(row._mapping) for row in rows]

        return {
            "success": True,
            "message": "Data fetched successfully." if data else "No record found.",
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