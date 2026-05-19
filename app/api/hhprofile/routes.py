from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.deps import get_current_user, require_access
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/api/hhprofile", tags=["HH PROFILE"])

@router.get("/")
async def list_hh_profile(
    hhid: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_access)
):
    sql = "SELECT * FROM users WHERE 1=1"
    params = {}

    if hhid:
        sql += " AND id = :hhid"
        params["hhid"] = f"%{hhid}%"

    result = await db.execute(text(sql), params)
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]