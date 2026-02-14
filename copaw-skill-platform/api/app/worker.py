import time

from sqlalchemy import text

from .db import SessionLocal
from .models import JobStatus, SkillVersion


POLL_SECONDS = 1.5


def claim_next_job():
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                WITH candidate AS (
                  SELECT id
                  FROM run_jobs
                  WHERE status = 'pending'
                  ORDER BY created_at ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE run_jobs j
                SET status = 'running', updated_at = now()
                FROM candidate
                WHERE j.id = candidate.id
                RETURNING j.id, j.skill_id, j.input_text;
                """
            )
        ).first()
        db.commit()
        return row
    finally:
        db.close()


def complete_job(job_id: str, output_text: str):
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE run_jobs
                SET status = :status, output_text = :output_text, updated_at = now()
                WHERE id = :job_id
                """
            ),
            {"status": JobStatus.completed.value, "output_text": output_text, "job_id": job_id},
        )
        db.commit()
    finally:
        db.close()


def fail_job(job_id: str, error_text: str):
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE run_jobs
                SET status = :status, error_text = :error_text, updated_at = now()
                WHERE id = :job_id
                """
            ),
            {"status": JobStatus.failed.value, "error_text": error_text, "job_id": job_id},
        )
        db.commit()
    finally:
        db.close()


def build_output(skill_id: int, user_input: str) -> str:
    db = SessionLocal()
    try:
        latest = (
            db.query(SkillVersion)
            .filter(SkillVersion.skill_id == skill_id)
            .order_by(SkillVersion.version.desc())
            .first()
        )
        if not latest:
            return "No skill version found."
        preview = latest.skill_md[:400].replace("\n", " ")
        return (
            "Simulated runner output (replace with sandbox execution).\n\n"
            f"User input: {user_input}\n"
            f"Skill version: v{latest.version}\n"
            f"Skill preview: {preview}"
        )
    finally:
        db.close()


def main():
    print("Worker started.")
    while True:
        row = claim_next_job()
        if not row:
            time.sleep(POLL_SECONDS)
            continue

        job_id, skill_id, input_text = row
        try:
            output = build_output(skill_id=skill_id, user_input=input_text or "")
            time.sleep(1.0)
            complete_job(str(job_id), output)
            print(f"completed job {job_id}")
        except Exception as exc:
            fail_job(str(job_id), str(exc))
            print(f"failed job {job_id}: {exc}")


if __name__ == "__main__":
    main()
