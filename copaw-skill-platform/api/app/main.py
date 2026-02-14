from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .auth import create_access_token, decode_token, hash_password, verify_password
from .db import Base, engine, get_db
from .models import (
    CollaboratorRole,
    JobStatus,
    RunJob,
    Skill,
    SkillCollaborator,
    SkillVersion,
    User,
)
from .schemas import (
    CollaboratorRequest,
    JobOut,
    LoginRequest,
    RegisterRequest,
    RunRequest,
    SkillCreateRequest,
    SkillDetailOut,
    SkillOut,
    SkillUpdateRequest,
    SkillVersionOut,
    TokenResponse,
    UserOut,
)


app = FastAPI(title="CoPaw Skill Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return parts[1]


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(authorization)
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def _can_view_skill(skill: Skill, user: User, db: Session) -> bool:
    if skill.owner_id == user.id:
        return True
    if skill.visibility == skill.visibility.public:
        return True
    collab = db.execute(
        select(SkillCollaborator).where(
            SkillCollaborator.skill_id == skill.id,
            SkillCollaborator.user_id == user.id,
        )
    ).scalar_one_or_none()
    if collab:
        return True
    if skill.visibility == skill.visibility.shared and collab:
        return True
    return False


def _can_edit_skill(skill: Skill, user: User, db: Session) -> bool:
    if skill.owner_id == user.id:
        return True
    collab = db.execute(
        select(SkillCollaborator).where(
            SkillCollaborator.skill_id == skill.id,
            SkillCollaborator.user_id == user.id,
            SkillCollaborator.role == CollaboratorRole.editor,
        )
    ).scalar_one_or_none()
    return collab is not None


def _latest_version(db: Session, skill_id: int) -> SkillVersion:
    latest = db.execute(
        select(SkillVersion)
        .where(SkillVersion.skill_id == skill_id)
        .order_by(SkillVersion.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not latest:
        raise HTTPException(status_code=500, detail="Skill has no version")
    return latest


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def web_root():
    file_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(file_path)


@app.post("/auth/register", response_model=UserOut)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    exists = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id, user.email))


@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/skills", response_model=SkillDetailOut)
def create_skill(
    payload: SkillCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = Skill(
        owner_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description,
        visibility=payload.visibility,
    )
    db.add(skill)
    db.flush()
    version = SkillVersion(
        skill_id=skill.id,
        version=1,
        skill_md=payload.skill_md,
        openai_yaml=payload.openai_yaml,
        created_by=current_user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(skill)
    db.refresh(version)
    return SkillDetailOut(skill=skill, latest_version=version, can_edit=True, can_run=True)


@app.get("/skills", response_model=list[SkillOut])
def list_skills(
    include_public: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Skill).outerjoin(
        SkillCollaborator,
        (SkillCollaborator.skill_id == Skill.id) & (SkillCollaborator.user_id == current_user.id),
    )
    conditions = [Skill.owner_id == current_user.id, SkillCollaborator.user_id == current_user.id]
    if include_public:
        conditions.append(Skill.visibility == Skill.visibility.public)
    rows = db.execute(q.where(or_(*conditions)).order_by(Skill.updated_at.desc())).scalars().all()
    # de-dup caused by join
    uniq = {s.id: s for s in rows}
    return list(uniq.values())


@app.get("/skills/{skill_id}", response_model=SkillDetailOut)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if not _can_view_skill(skill, current_user, db):
        raise HTTPException(status_code=403, detail="Forbidden")
    latest = _latest_version(db, skill.id)
    can_edit = _can_edit_skill(skill, current_user, db)
    return SkillDetailOut(skill=skill, latest_version=latest, can_edit=can_edit, can_run=True)


@app.put("/skills/{skill_id}", response_model=SkillDetailOut)
def update_skill(
    skill_id: int,
    payload: SkillUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if not _can_edit_skill(skill, current_user, db):
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.description is not None:
        skill.description = payload.description
    if payload.visibility is not None:
        skill.visibility = payload.visibility

    latest = _latest_version(db, skill.id)
    skill_md = payload.skill_md if payload.skill_md is not None else latest.skill_md
    openai_yaml = payload.openai_yaml if payload.openai_yaml is not None else latest.openai_yaml
    next_version = db.execute(
        select(func.coalesce(func.max(SkillVersion.version), 0) + 1).where(SkillVersion.skill_id == skill.id)
    ).scalar_one()
    new_version = SkillVersion(
        skill_id=skill.id,
        version=int(next_version),
        skill_md=skill_md,
        openai_yaml=openai_yaml,
        created_by=current_user.id,
    )
    db.add(new_version)
    db.commit()
    db.refresh(skill)
    db.refresh(new_version)
    return SkillDetailOut(skill=skill, latest_version=new_version, can_edit=True, can_run=True)


@app.get("/skills/{skill_id}/versions", response_model=list[SkillVersionOut])
def list_versions(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if not _can_view_skill(skill, current_user, db):
        raise HTTPException(status_code=403, detail="Forbidden")
    versions = db.execute(
        select(SkillVersion)
        .where(SkillVersion.skill_id == skill_id)
        .order_by(SkillVersion.version.desc())
    ).scalars().all()
    return versions


@app.post("/skills/{skill_id}/collaborators")
def add_collaborator(
    skill_id: int,
    payload: CollaboratorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can manage collaborators")
    target = db.execute(select(User).where(User.email == payload.user_email)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    collab = db.execute(
        select(SkillCollaborator).where(
            SkillCollaborator.skill_id == skill.id,
            SkillCollaborator.user_id == target.id,
        )
    ).scalar_one_or_none()
    if collab:
        collab.role = payload.role
    else:
        db.add(SkillCollaborator(skill_id=skill.id, user_id=target.id, role=payload.role))
    db.commit()
    return {"ok": True}


@app.post("/skills/{skill_id}/run", response_model=JobOut)
def run_skill(
    skill_id: int,
    payload: RunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if not _can_view_skill(skill, current_user, db):
        raise HTTPException(status_code=403, detail="Forbidden")
    job = RunJob(
        skill_id=skill.id,
        requested_by=current_user.id,
        input_text=payload.input_text,
        status=JobStatus.pending,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(RunJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    skill = db.get(Skill, job.skill_id)
    if not skill or not _can_view_skill(skill, current_user, db):
        raise HTTPException(status_code=403, detail="Forbidden")
    return job
