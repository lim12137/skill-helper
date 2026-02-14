import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import CollaboratorRole, JobStatus, SkillVisibility


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: dt.datetime


class SkillCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    visibility: SkillVisibility = SkillVisibility.private
    skill_md: str = Field(min_length=1)
    openai_yaml: str = Field(min_length=1)


class SkillUpdateRequest(BaseModel):
    description: str | None = None
    visibility: SkillVisibility | None = None
    skill_md: str | None = None
    openai_yaml: str | None = None


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: str
    visibility: SkillVisibility
    created_at: dt.datetime
    updated_at: dt.datetime


class SkillVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int
    version: int
    skill_md: str
    openai_yaml: str
    created_by: int
    created_at: dt.datetime


class SkillDetailOut(BaseModel):
    skill: SkillOut
    latest_version: SkillVersionOut
    can_edit: bool
    can_run: bool


class CollaboratorRequest(BaseModel):
    user_email: EmailStr
    role: CollaboratorRole


class RunRequest(BaseModel):
    input_text: str = ""


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_id: int
    requested_by: int
    input_text: str
    status: JobStatus
    output_text: str
    error_text: str
    created_at: dt.datetime
    updated_at: dt.datetime
