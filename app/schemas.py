from datetime import date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class RefreshIn(BaseModel):
    refresh_token: str

class StatusIn(BaseModel):
    status: str

class RegisterIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = "trainee"
    barangay_id: Optional[int] = None
    phone: Optional[str] = None
    psgc: Optional[str] = None

class ClientGroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    barangay_id: Optional[int] = None
    status: str = "active"
    participant_ids: List[int] = []

class ClientGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    barangay_id: Optional[int] = None
    status: Optional[str] = None
    participant_ids: Optional[List[int]] = None

class UploadMetadataIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role_id: int
    barangay_id: Optional[int] = None
    phone: Optional[str] = None
    psgc: Optional[str] = None
    status: str = "active"
    session_ids: List[int] = []

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    role_id: Optional[int] = None
    barangay_id: Optional[int] = None
    phone: Optional[str] = None
    psgc: Optional[str] = None
    status: Optional[str] = None
    session_ids: Optional[List[int]] = None

class SessionIdsIn(BaseModel):
    session_ids: List[int]

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2)
    description: Optional[str] = None
    color: str = "blue"
    permission_keys: List[str] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    permission_keys: Optional[List[str]] = None

class MaterialCreate(BaseModel):
    title: str = Field(..., min_length=2)
    description: Optional[str] = None
    category: Optional[str] = None
    number_of_lessons: int = 0
    total_duration: Optional[str] = None
    status: str = "active"

class MaterialUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    number_of_lessons: Optional[int] = None
    total_duration: Optional[str] = None
    status: Optional[str] = None

class LessonCreate(BaseModel):
    title: str
    lesson_number: int
    duration_minutes: int = 0
    order_index: int = 0

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    lesson_number: Optional[int] = None
    duration_minutes: Optional[int] = None
    order_index: Optional[int] = None

class ScheduleCreate(BaseModel):
    material_id: Optional[int] = None
    session_title: str
    date: date
    time: str
    location: Optional[str] = None
    barangay_id: int
    participant_ids: List[int] = []

class ScheduleUpdate(BaseModel):
    material_id: Optional[int] = None
    session_title: Optional[str] = None
    date: Optional[date] = None
    time: Optional[str] = None
    location: Optional[str] = None
    barangay_id: Optional[int] = None
    status: Optional[str] = None
    participant_ids: Optional[List[int]] = None

class ParticipantIdsIn(BaseModel):
    participant_ids: List[int]

class AttendanceItem(BaseModel):
    user_id: int
    status: str

class AttendanceIn(BaseModel):
    attendance: List[AttendanceItem]

class MappingCreate(BaseModel):
    session_id: int
    material_ids: List[int]

class MappingUpdate(BaseModel):
    session_id: Optional[int] = None
    material_ids: Optional[List[int]] = None
