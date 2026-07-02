# Ops‑Pilot

> **AI‑powered DevOps autopilot** – automatically detects CI/CD failures, scrapes GitHub Actions logs, summarises incidents with an LLM, and notifies your team via Slack or Discord.

[![CI](https://github.com/mohameeed22/ops-pilot-/actions/workflows/ci.yml/badge.svg)](https://github.com/mohameeed22/ops-pilot-/actions/workflows/ci.yml)

---

## ✨ Features

| Feature | Details |
|---------|---------|
| **GitHub Webhook handling** | Receives push, PR, and `workflow_run` events with HMAC-SHA256 signature verification and replay-attack protection |
| **CI failure detection** | Detects failed workflow runs and queues a log-scraping job automatically |
| **Log parsing** | Downloads and parses GitHub Actions log archives to extract error type, file, line number, and traceback |
| **LLM incident summaries** | Generates a concise 2–3 sentence AI-written incident summary via OpenAI |
| **Parallel notifications** | Posts rich embedded alerts to Slack and Discord simultaneously |
| **Retry + dead-letter queue** | Automatic retries with exponential back-off; permanently failed jobs go to a dead-letter Redis list |
| **Audit log** | Every webhook and worker action is recorded in a PostgreSQL `audit_events` table |
| **REST API** | Paginated `/runs`, `/stats`, `/audit` endpoints protected by API key auth |
| **Prometheus metrics** | `/metrics` endpoint scraped by the bundled Prometheus container |
| **Readiness probe** | `/ready` checks DB + Redis connectivity |
| **React Dashboard** | Full-featured dark-mode UI with stats, charts, run table, run detail, audit log, and health page |
| **Docker Compose** | One-command local stack: API + Worker + DB + Redis + Frontend + Prometheus |
| **GitHub Actions CI** | Lints, type-checks, and builds Docker images on every PR |

---

## 🏗️ Architecture

```
GitHub  ──POST──▶  FastAPI /api/v1/webhooks
                        │
                   ┌────▼────┐
                   │  Redis  │  (job queue + nonce store)
                   └────┬────┘
                        │
                   ┌────▼────┐
                   │ Worker  │  (pulls jobs, parses logs, calls LLM)
                   └────┬────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
       PostgreSQL             Slack / Discord
      (pipeline_runs,         notifications
       audit_events,
       api_keys)
            ▲
            │
     React Dashboard
    (port 5173 / 3000)
```

---

## 📦 Installation

### Prerequisites
- Docker Desktop (recommended) **or** Python 3.11+ and Node 20+
- A GitHub App (or Personal Access Token) with `actions:read` permission
- A GitHub webhook configured to send `workflow_run` events

### Docker Compose (recommended)

```bash
# 1. Clone
git clone https://github.com/mohameeed22/ops-pilot-.git
cd ops-pilot-

# 2. Configure environment
copy .env.example .env
notepad .env   # fill in GITHUB_APP_ID, GITHUB_PRIVATE_KEY, GITHUB_WEBHOOK_SECRET, SEED_API_KEY

# 3. Start everything
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health
# → {"status":"healthy","project":"AI DevOps Autopilot","debug_mode":true}
```

**Services exposed:**
| Service | URL |
|---------|-----|
| FastAPI API | http://localhost:8000 |
| Interactive API Docs | http://localhost:8000/api/v1/docs |
| React Dashboard | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

### Local development (without Docker)

```powershell
# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev          # → http://localhost:5173
```

---

## 🔑 API Key Setup

The dashboard uses `X-API-Key` header authentication.

1. Set `SEED_API_KEY=mysecretkey` in your `.env`.
2. On first startup, the API auto-creates this key in the database.
3. Set the same value in `frontend/.env` as `VITE_API_KEY=mysecretkey`.

---

## 📡 Sending a Test Webhook

```powershell
$payload = @{
    action = "completed"
    repository = @{ full_name = "myorg/myrepo" }
    workflow_run = @{
        id = 123456; html_url = "https://github.com/..."; conclusion = "failure"
        head_branch = "main"; head_sha = "deadbeefcafe1234567890abcdef1234567890ab"
        name = "CI Pipeline"
    }
    installation = @{ id = 99999 }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri http://localhost:8000/api/v1/webhooks `
    -Method Post -Body $payload -ContentType "application/json" `
    -Headers @{ "X-GitHub-Event" = "workflow_run"; "X-GitHub-Delivery" = [guid]::NewGuid().ToString() }
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

## 📜 License

MIT License – see `LICENSE` for details.

---

*Happy automating! 🎉*