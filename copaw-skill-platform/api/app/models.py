import datetime as dt
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class SkillVisibility(str, enum.Enum):
    private = "private"
    shared = "shared"
    public = "public"


class CollaboratorRole(str, enum.Enum):
    editor = "editor"
    viewer = "viewer"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visibility: Mapped[SkillVisibility] = mapped_column(
        Enum(SkillVisibility, name="skill_visibility"),
        default=SkillVisibility.private,
        nullable=False,
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False
    )

    versions = relationship("SkillVersion", back_populates="skill", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_owner_skill_name"),)


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    skill_md: Mapped[str] = mapped_column(Text, nullable=False)
    openai_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    skill = relationship("Skill", back_populates="versions")

    __table_args__ = (UniqueConstraint("skill_id", "version", name="uq_skill_version"),)


class SkillCollaborator(Base):
    __tablename__ = "skill_collaborators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    role: Mapped[CollaboratorRole] = mapped_column(
        Enum(CollaboratorRole, name="collaborator_role"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("skill_id", "user_id", name="uq_skill_user"),)


class RunJob(Base):
    __tablename__ = "run_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), index=True, nullable=False)
    requested_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.pending, nullable=False
    )
    output_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False
    )
