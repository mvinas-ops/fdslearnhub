from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import User, Role, RolePermission
from app.schemas import LoginIn, RefreshIn, RegisterIn
from app.auth import verify_password, hash_password, create_access_token, create_refresh_token, decode_token
from app.deps import get_current_user, permission_keys
from app.response import success_response

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/login")
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).options(selectinload(User.role_obj).selectinload(Role.permissions).selectinload(RolePermission.permission)).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active or user.status != "active":
        raise HTTPException(status_code=403, detail="Account is inactive")
    role = user.role_obj.slug if user.role_obj else user.role
    token_data = {"sub": str(user.id), "email": user.email, "role": role}
    access_token = create_access_token(token_data)
    refresh_token, expiry = create_refresh_token(token_data)
    user.refresh_token = refresh_token
    user.refresh_token_expiry = expiry
    user.last_login = datetime.utcnow()
    await db.commit()
    return success_response({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"id": user.id, "full_name": user.full_name, "email": user.email, "role": role, "permissions": sorted(permission_keys(user))},
    }, "Login successful")

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return success_response({"id": user.id, "full_name": user.full_name, "email": user.email, "role": user.role_obj.slug if user.role_obj else user.role, "permissions": sorted(permission_keys(user))})

@router.post("/logout")
async def logout(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.refresh_token = None
    user.refresh_token_expiry = None
    await db.commit()
    return success_response(None, "Logged out")

@router.post("/refresh")
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
        user_id = int(decoded.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await db.get(User, user_id)
    if not user or user.refresh_token != payload.refresh_token or not user.refresh_token_expiry or user.refresh_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    role = user.role_obj.slug if user.role_obj else user.role
    access = create_access_token({"sub": str(user.id), "email": user.email, "role": role})
    new_refresh, expiry = create_refresh_token({"sub": str(user.id), "email": user.email, "role": role})
    user.refresh_token = new_refresh; user.refresh_token_expiry = expiry
    await db.commit()
    return success_response({"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"})


@router.post("/create-account", tags=["Auth - Create Account"])
@router.post("/register", tags=["Auth - Create Account"])
async def create_account(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    """Public account creation for trainee/client accounts. Admin/CML accounts should still be created by Admin User Management."""
    if await db.scalar(select(User.id).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    role_slug = payload.role.lower().strip()
    allowed_public_roles = {"trainee", "client"}
    if role_slug not in allowed_public_roles:
        raise HTTPException(status_code=403, detail="Only trainee/client self-registration is allowed")
    role = (await db.execute(select(Role).where(Role.slug == "trainee"))).scalar_one_or_none()
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password=hash_password(payload.password),
        role="trainee",
        role_id=role.id if role else None,
        barangay_id=payload.barangay_id,
        phone=payload.phone,
        psgc=payload.psgc,
        status="active",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return success_response({"id": user.id, "full_name": user.full_name, "email": user.email, "role": user.role}, "Account created")
