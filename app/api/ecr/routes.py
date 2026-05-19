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

router = CustomRouter(prefix="/api/ecr", tags=["ECR"])

@router.post("/ec_result")
async def eligibility_check_result(
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
                a.set_group AS `Set Group`,
                a.hh_id AS `Listahanan ID`,
                a.last_name AS `Lastname`,
                a.first_name AS `Firstname`,
                a.mid_name AS `Middlename`,
                a.ext_name AS `Extension Name`,
                IF(a.sex = 1, 'Male', 'Female') AS `Sex`,
                a.reckon_date AS `Date of Reckoning`,
                a.birthday AS `Date of Birth`,
                a.age_as_of_reckon AS `Age as of Reckoning`,
                a.relation_to_head AS `Relation to Head`,
                IF(a.elig_pregnant = 1, 'YES', 'NO') AS `Eligible Pregnant`,
                IF(a.elig_child = 1, 'YES', 'NO') AS `Eligible Child`,
                IF(a.eligible = 1, 'YES', 'NO') AS `Eligible Member`
                FROM
                tbl_ec_result_v3_ods a
                WHERE
                a.hh_id = :hh_id
                AND a.is_official = 1
            ORDER BY `Relation to Head`, `Age as of Reckoning` DESC
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
            tbl_ec_result_v3_ods a
                WHERE
            a.hh_id = :hh_id
            AND a.is_official = 1
            ORDER BY `Relation to Head`, `Age as of Reckoning` DESC
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
