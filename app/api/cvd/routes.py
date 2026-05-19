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

router = CustomRouter(prefix="/api/cvd", tags=["CVD"])

@router.post("/compliance")
async def list_cv_compliance(
    hh_id: int,
    period_id: int,
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Records per page"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_access),
):
    try:
        offset = (page - 1) * limit

        base_query = """
            SELECT
                a.cvgen_cs_name `CV Form Generation Household Status`,
                a.napa_cs_name `CV Result Household Status`,
                a.`compliance type`
                a.sex,
                a.fullname,
                a.person_id `Member ID`,
                a.age `Age`,
                a.date_of_birth `Date of Birth`,
                a.school,
                a.grade `Current Grade Level`,
                a.attending_school
                a.educ_compliance `School Attendance`,
                a.payroll_type_desc,
                a.amount `Education Grant`,
                a.hc, -- Health Center
                a.hcv_component1,
                a.hcv_component2,
                a.barangay `FDS Location`,
                a.fds_component1,
                a.fds_component2,
                a.school `Deworm Location`,
                a.deworm_component1,
                a.deworm_component2,
                a.napa_transaction_id `CVR Transaction`,
                a.napa_status,
                a.payroll_batch_id `Paryoll Batch`,
                a.payment_status_name,
                a.total_educ `Total Educ Grant`,
                a.health_amount `Health Grant`,
                a.f1kd_amount `F1KD`,
                a.rice_amount `Rice Subsidy`,
                a.napa_payroll_desc,
                a.total_grant `Total Grant`
                FROM
                tbl_beneficiary_compliance_v3_ods a
                WHERE
                a.household_id = :hh_id
                AND a.period_id = :period_id
        """

        params = {
            "hh_id": hh_id,
            "period_id": period_id,
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
                tbl_beneficiary_compliance_v3_ods a
                WHERE
                a.household_id = :hh_id
                AND a.period_id = :period_id
        """

        count_params = {
            "hh_id": hh_id,
            "period_id": period_id
        }

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
