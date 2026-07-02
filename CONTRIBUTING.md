# Contributing to Ops‑Pilot

Thank you for your interest in contributing! This guide covers the local setup, code style, and PR process.

---

## Development Setup

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pip install ruff mypy
uvicorn backend.app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

---

## Code Style

### Python
- **Formatter / Linter:** [`ruff`](https://docs.astral.sh/ruff/) – run `ruff check backend/ --fix`
- **Type hints:** All functions must have type annotations; checked with `mypy`
- **Docstrings:** Required on all public functions/classes

### JavaScript / React
- **ESLint** is configured via Vite defaults – run `npm run lint` in `frontend/`
- Functional components only (no class components)
- Use named exports

---

## PR Checklist

Before opening a pull request, ensure:

- [ ] `ruff check backend/` passes with no errors
- [ ] `mypy backend/app --ignore-missing-imports` passes
- [ ] `npm run lint` in `frontend/` passes
- [ ] New features have at least a manual test description in the PR body
- [ ] `docker-compose up -d` starts cleanly and `/health` returns `200`
- [ ] Commit messages follow the format: `type(scope): description` (e.g. `feat(api): add run retry endpoint`)

---

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code; protected; requires PR |
| `feat/…` | New features |
| `fix/…` | Bug fixes |
| `chore/…` | Dependency updates, CI tweaks |

---

## Reporting Issues

Open a GitHub Issue with:
1. Steps to reproduce
2. Expected vs actual behaviour
3. Relevant log output (sanitise secrets!)
