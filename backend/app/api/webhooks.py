import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, Header, Depends, status, BackgroundTasks
from app.core.config import settings

# Setup simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhooks")

router = APIRouter(prefix="/webhooks", tags=["GitHub Webhooks"])

async def run_pipeline_task(repo_name: str, run_id: int, installation_id: int):
    """Background task runner to download and parse failed workflow logs."""
    try:
        from app.services.pipeline import pipeline_coordinator
        result = await pipeline_coordinator.process_failed_run(repo_name, run_id, installation_id)
        logger.info(f"Pipeline finished processing run {run_id}. Result: {result}")
    except Exception as e:
        logger.error(f"Failed to process background pipeline for run {run_id}: {e}")

async def verify_github_signature(
    request: Request,
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256")
):
    """Dependency that verifies the incoming GitHub webhook payload signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET is not set. Signature verification bypassed.")
        return

    if not x_hub_signature_256.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature format is invalid. Must start with sha256="
        )

    # Clean the signature header value
    signature_hash = x_hub_signature_256.replace("sha256=", "")

    # Read the raw request body
    body = await request.body()

    # Calculate local signature using Webhook Secret
    mac = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    )
    local_signature = mac.hexdigest()

    # Time-attack-safe equality check
    if not hmac.compare_digest(signature_hash, local_signature):
        logger.warning("Received webhook with invalid HMAC signature.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HMAC signature verification failed"
        )


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_github_signature)]
)
async def github_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery")
):
    """Processes incoming GitHub webhook events.
    
    Accepts the payload asynchronously after verifying the sender's signature.
    """
    logger.info(f"Received webhook event '{x_github_event}' (Delivery ID: {x_github_delivery})")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    # Handle standard Ping event (sent when webhook is first created)
    if x_github_event == "ping":
        logger.info("Handling webhook ping verification.")
        return {"message": "pong", "zen": payload.get("zen", "")}

    # Handle workflow run updates
    elif x_github_event == "workflow_run":
        action = payload.get("action")
        workflow_run = payload.get("workflow_run", {})
        conclusion = workflow_run.get("conclusion")
        repo_name = payload.get("repository", {}).get("full_name")

        logger.info(
            f"Workflow run event received: Action={action}, "
            f"Conclusion={conclusion}, Repo={repo_name}"
        )

        if action == "completed" and conclusion == "failure":
            run_id = workflow_run.get("id")
            run_url = workflow_run.get("html_url")
            branch = workflow_run.get("head_branch")
            commit_sha = workflow_run.get("head_sha")
            installation_id = payload.get("installation", {}).get("id")

            if not installation_id:
                logger.error("Missing installation ID in webhook payload")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing installation ID in payload"
                )

            logger.error(
                f"🚨 CI FAILURE DETECTED: Run #{run_id} in {repo_name} "
                f"on branch {branch} (Commit: {commit_sha[:7]}). Queueing log scraper..."
            )

            # Trigger pipeline processing task in the background
            background_tasks.add_task(
                run_pipeline_task,
                repo_name,
                run_id,
                installation_id
            )

            return {
                "status": "queued",
                "message": f"Queued log downloading and parsing for run {run_id}",
                "details": {
                    "repository": repo_name,
                    "branch": branch,
                    "commit_sha": commit_sha,
                    "run_url": run_url
                }
            }

    # Catch-all for other events we register for
    logger.info(f"Event '{x_github_event}' bypassed (no handler).")
    return {"status": "bypassed", "event": x_github_event}
