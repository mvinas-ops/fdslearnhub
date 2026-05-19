from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from .database import Base

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    module = Column(String(100), nullable=True)

class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(30), default="blue")
    is_system_role = Column(Boolean, default=False, nullable=False)
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("User", back_populates="role_obj")

class RolePermission(Base):
    __tablename__ = "role_permissions"
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

class Barangay(Base, TimestampMixin):
    __tablename__ = "barangays"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    psgc = Column(String(32), nullable=True, index=True)

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, default="Unnamed User")
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50), default="trainee", index=True)  # backward-compatible with uploaded project
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=True)
    phone = Column(String(50), nullable=True)
    psgc = Column(String(32), nullable=True)
    status = Column(String(30), default="active", index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    refresh_token = Column(String(2048), nullable=True)
    refresh_token_expiry = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    role_obj = relationship("Role", back_populates="users")
    barangay = relationship("Barangay")
    assigned_barangays = relationship("CMLBarangay", back_populates="cml", cascade="all, delete-orphan")

class CMLBarangay(Base):
    __tablename__ = "cml_barangays"
    id = Column(Integer, primary_key=True)
    cml_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    barangay_id = Column(Integer, ForeignKey("barangays.id", ondelete="CASCADE"), nullable=False)
    cml = relationship("User", back_populates="assigned_barangays")
    barangay = relationship("Barangay")
    __table_args__ = (UniqueConstraint("cml_user_id", "barangay_id", name="uq_cml_barangay"),)

class TrainingMaterial(Base, TimestampMixin):
    __tablename__ = "training_materials"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    number_of_lessons = Column(Integer, default=0)
    total_duration = Column(String(80), nullable=True)
    status = Column(String(30), default="active", index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    lessons = relationship("Lesson", back_populates="material", cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="material", cascade="all, delete-orphan")

class Lesson(Base, TimestampMixin):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey("training_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    duration_minutes = Column(Integer, default=0)
    order_index = Column(Integer, default=0)
    material = relationship("TrainingMaterial", back_populates="lessons")
    __table_args__ = (UniqueConstraint("material_id", "lesson_number", name="uq_material_lesson_number"),)

class LessonProgress(Base, TimestampMixin):
    __tablename__ = "lesson_progress"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    lesson = relationship("Lesson")
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress"),)

class Resource(Base, TimestampMixin):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey("training_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    stored_file_name = Column(String(255), nullable=True)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, default=0)
    file_path = Column(String(500), nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    material = relationship("TrainingMaterial", back_populates="resources")
    uploaded_by = relationship("User")

class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey("training_materials.id"), nullable=True)
    session_title = Column(String(255), nullable=False, index=True)
    session_date = Column(Date, nullable=False, index=True)
    session_time = Column(String(10), nullable=False)
    location = Column(String(255), nullable=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False, index=True)
    status = Column(String(30), default="upcoming", index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    material = relationship("TrainingMaterial")
    barangay = relationship("Barangay")
    participants = relationship("ScheduleParticipant", back_populates="schedule", cascade="all, delete-orphan")
    mapped_materials = relationship("SessionMaterialMapping", back_populates="schedule", cascade="all, delete-orphan")

class ScheduleParticipant(Base, TimestampMixin):
    __tablename__ = "schedule_participants"
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_status = Column(String(30), default="pending", index=True)  # pending, attended, absent
    schedule = relationship("Schedule", back_populates="participants")
    user = relationship("User")
    __table_args__ = (UniqueConstraint("schedule_id", "user_id", name="uq_schedule_participant"),)

class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), default="assigned")
    __table_args__ = (UniqueConstraint("user_id", "schedule_id", name="uq_user_session"),)

class SessionMaterialMapping(Base, TimestampMixin):
    __tablename__ = "session_material_mappings"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("training_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule = relationship("Schedule", back_populates="mapped_materials")
    material = relationship("TrainingMaterial")
    __table_args__ = (UniqueConstraint("session_id", "material_id", name="uq_session_material"),)

class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)


class ClientGroup(Base, TimestampMixin):
    __tablename__ = "client_groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=True, index=True)
    status = Column(String(30), default="active", index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    barangay = relationship("Barangay")
    created_by = relationship("User")
    members = relationship("ClientGroupMember", back_populates="group", cascade="all, delete-orphan")

class ClientGroupMember(Base, TimestampMixin):
    __tablename__ = "client_group_members"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("client_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group = relationship("ClientGroup", back_populates="members")
    user = relationship("User")
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_client_group_member"),)
