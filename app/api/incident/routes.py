from fastapi import Depends, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any, Optional

from app.database import get_db
from app.deps import require_access
from app.core.router import CustomRouter

from app.response import success_response, pagination_meta
from app.exceptions import DBException
from app.error_codes import DB_UNAVAILABLE

from sqlalchemy.exc import SQLAlchemyError

router = CustomRouter(prefix="/api/incident", tags=["Incident"])

@router.post("/hazard_incident")
async def hazard_incident(
    hh_id: str,
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Records per page"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_access),
):
    try:
        offset = (page - 1) * limit

        base_query = """
            SELECT
                a.hazard_incident AS `Hazard Incident`,
                a.hazard_type AS `Hazard Type`,
                a.hazard_subcategory `Hazard Subcategory`,
                a.date_occured AS `Date Occured`
                FROM
                tbl_household_v3 z
                INNER JOIN lib_psgc_barangay_v3 y ON z.barangay_id = y.barangay_id
                INNER JOIN tbl_incident_v3_ods a ON y.city_id = a.city_id
                WHERE
                z.listahanan_id = :hh_id
            ORDER BY `Date Occured` DESC, `Hazard Incident`
        """

        params = {
            "hh_id": hh_id,
            "limit": limit,
            "offset": offset
        }

        base_query += " LIMIT :limit OFFSET :offset"

        sql = text(base_query)

        result = await db.execute(sql, params)
        rows = result.fetchall()
        data = [dict(row._mapping) for row in rows]

        # COUNT query
        count_query = """
            SELECT
            count(*)
            FROM
            tbl_household_v3 z
            INNER JOIN lib_psgc_barangay_v3 y ON z.barangay_id = y.barangay_id
            INNER JOIN tbl_incident_v3_ods a ON y.city_id = a.city_id
            WHERE
            z.listahanan_id = :hh_id
            ORDER BY `Date Occured` DESC, `Hazard Incident`;
        """

        count_params = {
            "hh_id": hh_id
        }

        if year is not None:
            count_query += " AND for_year = :year"
            count_params["year"] = year
        
        if month is not None:
            count_query += " AND for_month = :month"
            count_params["month"] = month

        count_sql = text(count_query)
        count_result = await db.execute(count_sql, count_params)

        total = count_result.scalar_one()

    except SQLAlchemyError:
        raise DBException(
            message="Database unavailable",
            error_code=DB_UNAVAILABLE,
            status_code=503
        )

    return success_response(
        data=data,
        message="Data fetched successfully." if data else "No Record found.",
        meta=pagination_meta(page, limit, total)
    )

