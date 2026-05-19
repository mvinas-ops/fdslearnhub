import re
from datetime import date, datetime
from typing import Iterable
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import AuditLog, LessonProgress, SessionMaterialMapping, ScheduleParticipant

MAX_LIMIT = 100

def clean_search(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"[%_\\]", "", value.strip())
    return value[:80] or None

def normalize_slug(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "item"

def page_params(page: int = 1, limit: int = 20):
    return max(page, 1), min(max(limit, 1), MAX_LIMIT)

def dt_to_iso(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value

async def audit(db: AsyncSession, actor_id: int | None, action: str, entity: str, entity_id: int | None = None, details: str | None = None):
    db.add(AuditLog(actor_user_id=actor_id, action=action, entity=entity, entity_id=entity_id, details=details))

async def material_progress(db: AsyncSession, user_id: int, material_id: int) -> int:
    from .models import Lesson
    total = await db.scalar(select(func.count(Lesson.id)).where(Lesson.material_id == material_id)) or 0
    if total == 0:
        return 0
    completed = await db.scalar(
        select(func.count(LessonProgress.id))
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .where(Lesson.material_id == material_id, LessonProgress.user_id == user_id, LessonProgress.is_completed == True)
    ) or 0
    return round((completed / total) * 100)

async def user_unlocked_material_ids(db: AsyncSession, user_id: int) -> set[int]:
    rows = await db.execute(
        select(SessionMaterialMapping.material_id)
        .join(ScheduleParticipant, ScheduleParticipant.schedule_id == SessionMaterialMapping.session_id)
        .where(ScheduleParticipant.user_id == user_id, ScheduleParticipant.attendance_status == "attended")
    )
    return set(rows.scalars().all())
