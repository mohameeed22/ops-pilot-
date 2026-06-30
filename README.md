# Ops‑Pilot

A **Python‑powered DevOps autopilot** that automates common CI/CD, infrastructure, and monitoring tasks.  The project started as a proof‑of‑concept for an AI‑driven DevOps assistant (see the original design discussion in the repository).

## ✨ Features

- **GitHub webhook handling** – receive push events, PR events, etc.
- **Config‑driven pipelines** – define steps in `backend/app/core/config.py`.
- **Docker‑compose orchestration** – spin up services locally with `docker-compose.yml`.
- **Extensible services** – add new automation modules under `backend/app/services/`.

## 📦 Installation

1. **Clone the repo** (if you haven’t already):

   ```bash
   git clone https://github.com/mohameeed22/ops-pilot-.git
   cd ops-pilot-
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate   # PowerShell
   # or
   .\.venv\Scripts\activate.bat   # cmd
   ```

3. **Install dependencies**:

   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment variables**
   Copy the example file and edit as needed:

   ```bash
   copy .env.example .env
   # edit .env (GitHub secret, webhook secret, etc.)
   ```

## 🚀 Usage

Run the FastAPI application locally:

```bash
uvicorn backend.app.main:app --reload
```

The API will be available at **http://127.0.0.1:8000**.
Visit **http://127.0.0.1:8000/docs** for the interactive OpenAPI UI.

### Docker

You can also launch the whole stack with Docker Compose:

```bash
docker-compose up -d
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch:

   ```bash
   git checkout -b feat/your-feature
   ```
3. Make your changes and ensure tests (if any) pass.
4. Commit with a clear message and push:

   ```bash
   git push origin feat/your-feature
   ```
5. Open a Pull Request on GitHub.

## 📜 License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

*Happy automating!* 🎉