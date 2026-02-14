# CoPaw Skill Platform (Docker MVP)

## Start

```bash
docker compose up --build
```

Open: `http://localhost:8080`

## Included

- Multi-user auth (`register/login`)
- Skill create/edit with versioning
- Visibility (`private/shared/public`)
- Collaborator API (`editor/viewer`)
- Run job queue (worker process)
- Simple web UI for demo

## Notes

- Runner is simulated. Replace `app/worker.py` with real sandbox execution.
- Change `JWT_SECRET` and database password before production use.

## GitHub Actions multi-arch images

Workflow (repo root): `.github/workflows/copaw-skill-platform-docker-multiarch.yml`

- Build targets: `linux/amd64, linux/arm64`
- Registry: `ghcr.io/<owner>/<repo>/copaw-skill-platform`
- `pull_request`: build only (no push)
- `push main/tag` and `workflow_dispatch`: build + push

Before first push, ensure repository has:

1. Actions permissions with `Read and write permissions` for `GITHUB_TOKEN`
2. Package visibility configured in GHCR as needed
