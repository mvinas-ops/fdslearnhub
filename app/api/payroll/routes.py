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

router = CustomRouter(prefix="/api/payroll", tags=["PAYROLL"])


# @router.post("/wgrants")
# async def list_hh_withgrants(
#     year: int,
#     month: int,
#     region: int,
#     db: AsyncSession = Depends(get_db),
#     current_user: dict = Depends(require_access),
# ):
#     try:
#         sql = text("""
#             SELECT
#                 t1.listahanan_id,
#                 pt1.payroll_type_desc,
#                 t1.for_year AS year,
#                 t1.for_month,
#                 l1.name AS payment_mode_desc,
#                 t1.lbp_account,
#                 (t1.educ_amount + t1.educ_amount_3_5) AS educ_amount,
#                 t1.health_amount,
#                 t1.rice_amount,
#                 t1.f1kd_amount,
#                 (
#                     t1.educ_amount + t1.educ_amount_3_5 +
#                     t1.health_amount + t1.rice_amount + t1.f1kd_amount
#                 ) AS Amount,
#                 CASE 
#                     WHEN t1.claim_status = 1 OR LENGTH(t1.lbp_account) > 14
#                     THEN 'Yes' ELSE '' 
#                 END AS Received,
#                 l3.batch_status_name AS payment_status
#             FROM tbl_payroll_history_v3 t1
#             INNER JOIN lib_payment_mode l1
#                 ON l1.payment_mode_id = t1.payment_mode
#             INNER JOIN lib_payroll_type pt1
#                 ON pt1.payroll_type_id = t1.payroll_type
#             LEFT JOIN lib_month l2
#                 ON t1.for_month = l2.month_id
#             INNER JOIN tbl_payroll_transaction_log_v3
#                 ON t1.payroll_transaction_log_id =
#                    tbl_payroll_transaction_log_v3.payroll_transaction_log_id
#             LEFT JOIN lib_batch_status l3
#                 ON tbl_payroll_transaction_log_v3.batch_status = l3.batch_status_id
#             WHERE
#                 t1.payment_status IN (0)
#                 AND tbl_payroll_transaction_log_v3.batch_status = 3
#                 AND t1.for_year = :year
#                 AND t1.for_month = :month
#                 AND t1.psgc_region = :region
#         """)

#         result = await db.execute(sql, {
#             "year": year,
#             "month": month,
#             "region": region,
#         })

#         rows = result.fetchall()
#         data = [dict(row._mapping) for row in rows]

#     except SQLAlchemyError:
#         raise DBException(
#             message="Database unavailable",
#             error_code=DB_UNAVAILABLE,
#             status_code=503
#         )

#     return success_response(
#         data=data,
#         message="Data fetched successfully." if data else "No Record found."
#     )


@router.post("/grants")
async def list_hh_grants(
    hh_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Records per page"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_access),
):
    try:
        offset = (page - 1) * limit

        base_query = """
            SELECT *
            FROM vw_payroll_history_v2_ods
            WHERE listahanan_id = :hh_id
        """

        params = {
            "hh_id": hh_id,
            "limit": limit,
            "offset": offset
        }

        if year is not None:
            base_query += " AND for_year = :year"
            params["year"] = year

        if month is not None:
            base_query += " AND for_month = :month"
            params["month"] = month

        base_query += " LIMIT :limit OFFSET :offset"

        sql = text(base_query)

        result = await db.execute(sql, params)
        rows = result.fetchall()
        data = [dict(row._mapping) for row in rows]

        # COUNT query
        count_query = """
            SELECT COUNT(*)
            FROM vw_payroll_history_v2_ods
            WHERE listahanan_id = :hh_id
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

@router.post("/recovery")
async def list_recovery_overpayment(
    hh_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Records per page"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_access),
):
    try:
        offset = (page - 1) * limit

        base_query = """
            SELECT *
            FROM vw_recovery_of_overpayment_ods
            WHERE hh_id = :hh_id
        """

        params = {
            "hh_id": hh_id,
            "limit": limit,
            "offset": offset
        }

        if year is not None:
            base_query += " AND for_year = :year"
            params["year"] = year

        if month is not None:
            base_query += " AND for_month = :month"
            params["month"] = month

        base_query += " LIMIT :limit OFFSET :offset"

        sql = text(base_query)

        result = await db.execute(sql, params)
        rows = result.fetchall()
        data = [dict(row._mapping) for row in rows]

        # COUNT query
        count_query = """
            SELECT COUNT(*)
            FROM vw_recovery_of_overpayment_ods
            WHERE hh_id = :hh_id
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

