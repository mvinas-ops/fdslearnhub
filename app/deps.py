from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from .auth import decode_token
from .database import get_db
from .models import User, Role, RolePermission

security = HTTPBearer(auto_error=True)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(
        select(User).options(selectinload(User.role_obj).selectinload(Role.permissions).selectinload(RolePermission.permission)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.status != "active":
        raise HTTPException(status_code=401, detail="Inactive or missing user")
    return user

def role_slug(user: User) -> str:
    return (user.role_obj.slug if user.role_obj else user.role or "").lower()

def permission_keys(user: User) -> set[str]:
    keys = set()
    if user.role_obj:
        for rp in user.role_obj.permissions:
            if rp.permission:
                keys.add(rp.permission.key)
    if "full_access" in keys:
        keys.update({"view_training_materials","view_profile","receive_notifications","create_schedules","manage_participants","view_attendance","send_notifications","download_reports","manage_users","manage_training_materials","manage_roles","manage_session_material_mapping"})
    return keys

def require_role(*allowed: str):
    allowed_set = {a.lower() for a in allowed}
    async def checker(user: User = Depends(get_current_user)):
        slug = role_slug(user)
        if slug not in allowed_set and slug != "administrator":
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return checker

def require_permission(*required: str):
    async def checker(user: User = Depends(get_current_user)):
        if role_slug(user) == "administrator":
            return user
        keys = permission_keys(user)
        if not set(required).issubset(keys):
            raise HTTPException(status_code=403, detail="Missing permission")
        return user
    return checker

require_admin = require_role("administrator")
require_cml = require_role("cml", "community_leader")
require_trainee = require_role("trainee")
