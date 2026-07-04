import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, Request, HTTPException, Header, status, Depends
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import async_session
from app.models.pipeline import PipelineRun
from app.models.audit_event import AuditEvent
from app.services.queue import redis_queue

# Setup simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhooks")

router = APIRouter(prefix="/webhooks", tags=["GitHub Webhooks"])

_NONCE_TTL_SECONDS = 300  # 5 minutes – replay attack protection window


async def verify_github_signature(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256")
):
    """Dependency that verifies the incoming GitHub webhook payload signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET is not set. Signature verification bypassed.")
        return

    if not x_hub_signature_256:
        logger.warning("Signature verification failed: X-Hub-Signature-256 header is missing.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature header X-Hub-Signature-256 is missing"
        )

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


async def _write_audit(event_type: str, actor: str, resource_id: str | None, detail: str) -> None:
    """Helper to write an audit event row (best-effort, never raises)."""
    try:
        async with async_session() as db:
            async with db.begin():
                db.add(AuditEvent(
                    event_type=event_type,
                    actor=actor,
                    resource_id=resource_id,
                    detail=detail,
                ))
    except Exception as exc:
        logger.error(f"Audit write failed: {exc}")


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_github_signature)] if settings.GITHUB_WEBHOOK_SECRET else []
)
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery")
):
    """Processes incoming GitHub webhook events.

    Accepts the payload asynchronously after verifying the sender's signature.
    Implements replay-attack protection via Redis delivery-ID nonce store.
    """
    logger.info(f"Received webhook event '{x_github_event}' (Delivery ID: {x_github_delivery})")

    # --- Replay-attack protection ---
    nonce_key = f"webhook:nonce:{x_github_delivery}"
    try:
        redis_client = await redis_queue.get_redis()
        already_seen = await redis_client.set(nonce_key, "1", ex=_NONCE_TTL_SECONDS, nx=True)
        if already_seen is None:
            logger.warning(f"Duplicate webhook delivery ID detected: {x_github_delivery}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate webhook delivery – replay attack protection triggered"
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Redis nonce check failed (continuing anyway): {exc}")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    repo_name = payload.get("repository", {}).get("full_name", "unknown")

    # Handle standard Ping event (sent when webhook is first created)
    if x_github_event == "ping":
        logger.info("Handling webhook ping verification.")
        await _write_audit("webhook.ping", "github", repo_name, f"Delivery: {x_github_delivery}")
        return {"message": "pong", "zen": payload.get("zen", "")}

    # Handle workflow run updates
    elif x_github_event == "workflow_run":
        action = payload.get("action")
        workflow_run = payload.get("workflow_run", {})
        conclusion = workflow_run.get("conclusion")

        logger.info(
            f"Workflow run event received: Action={action}, "
            f"Conclusion={conclusion}, Repo={repo_name}"
        )

        await _write_audit(
            f"webhook.workflow_run.{action}",
            "github",
            repo_name,
            json.dumps({"conclusion": conclusion, "delivery": x_github_delivery})
        )

        if action == "completed" and conclusion == "success":
            run_id = workflow_run.get("id")
            logger.info(f"CI SUCCESS DETECTED: Run #{run_id} in {repo_name}. Checking for previous failure (flakiness)...")
            try:
                async with async_session() as db:
                    async with db.begin():
                        stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                        res = await db.execute(stmt)
                        db_run = res.scalar_one_or_none()
                        if db_run:
                            db_run.is_flaky = True
                            if db_run.error_filename and db_run.error_type:
                                sig = f"{db_run.error_filename}:{db_run.error_line_number}:{db_run.error_type}"
                                from app.models.flaky_test import FlakyTest
                                stmt_flaky = select(FlakyTest).where(FlakyTest.error_signature == sig)
                                res_flaky = await db.execute(stmt_flaky)
                                flaky_record = res_flaky.scalar_one_or_none()
                                if flaky_record:
                                    flaky_record.success_count += 1
                                    flaky_record.is_flaky = True
                                else:
                                    flaky_record = FlakyTest(
                                        repo_name=repo_name,
                                        workflow_name=db_run.workflow_name or "unknown",
                                        error_signature=sig,
                                        failure_count=1,
                                        success_count=1,
                                        is_flaky=True
                                    )
                                    db.add(flaky_record)
                            await db.commit()
                            logger.info(f"Run #{run_id} marked as FLAKY success.")
            except Exception as e:
                logger.error(f"Failed to process flaky success for run {run_id}: {e}")

        elif action == "completed" and conclusion == "failure":
            run_id = workflow_run.get("id")
            run_url = workflow_run.get("html_url")
            branch = workflow_run.get("head_branch")
            commit_sha = workflow_run.get("head_sha")
            workflow_name = workflow_run.get("name")
            installation_id = payload.get("installation", {}).get("id")
            
            pull_requests = workflow_run.get("pull_requests", [])
            pr_number = pull_requests[0].get("number") if pull_requests else None

            if not installation_id:
                logger.error("Missing installation ID in webhook payload")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing installation ID in payload"
                )

            logger.error(
                f"🚨 CI FAILURE DETECTED: Run #{run_id} in {repo_name} "
                f"on branch {branch} (Commit: {commit_sha[:7] if commit_sha else '?'}). Queueing log scraper..."
            )

            # 1. Insert/Update record as pending in DB
            try:
                async with async_session() as db:
                    async with db.begin():
                        stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                        res = await db.execute(stmt)
                        db_run = res.scalar_one_or_none()
                        if not db_run:
                            db_run = PipelineRun(
                                repo_name=repo_name,
                                run_id=run_id,
                                installation_id=installation_id,
                                status="pending",
                                branch=branch,
                                commit_sha=commit_sha,
                                run_url=run_url,
                                workflow_name=workflow_name,
                            )
                            db.add(db_run)
                        else:
                            db_run.status = "pending"
                            db_run.branch = branch
                            db_run.commit_sha = commit_sha
                            db_run.run_url = run_url
                            db_run.workflow_name = workflow_name
                        await db.commit()
            except Exception as e:
                logger.error(f"Failed to record pending pipeline run {run_id} in database: {e}")
                # We can continue and still queue the task even if DB logging fails temporarily

            # 2. Push enriched task to Redis Queue
            try:
                task_payload = {
                    "repo_name": repo_name,
                    "run_id": run_id,
                    "installation_id": installation_id,
                    "branch": branch,
                    "commit_sha": commit_sha,
                    "run_url": run_url,
                    "workflow_name": workflow_name,
                    "pr_number": pr_number,
                }
                await redis_queue.push_task("devops_pipeline_queue", task_payload)
            except Exception as e:
                logger.error(f"Failed to push task to Redis queue for run {run_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to queue task in Redis: {e}"
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
    await _write_audit(f"webhook.{x_github_event}.bypassed", "github", repo_name, f"Delivery: {x_github_delivery}")
    return {"status": "bypassed", "event": x_github_event}


@router.post("/bitbucket", status_code=status.HTTP_202_ACCEPTED)
async def bitbucket_webhook_handler(
    request: Request,
    x_event_key: str | None = Header(None, alias="X-Event-Key"),
):
    """Processes incoming Bitbucket webhook events."""
    logger.info(f"Received Bitbucket webhook event '{x_event_key}'")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if x_event_key not in ("repo:commit_status_created", "repo:commit_status_updated"):
        return {"status": "ignored", "event": x_event_key}

    commit_status = payload.get("commit_status", {})
    state = commit_status.get("state")
    repo_full = payload.get("repository", {}).get("full_name", "unknown")
    run_id = commit_status.get("key", 0)
    branch = commit_status.get("refname", "").replace("refs/heads/", "") if commit_status.get("refname") else None
    commit_sha = commit_status.get("commit", {}).get("hash")
    url = commit_status.get("url")
    name = commit_status.get("name")

    if state == "FAILED":
        logger.error(f"Bitbucket CI FAILURE: {repo_full}")

        try:
            async with async_session() as db:
                async with db.begin():
                    stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                    res = await db.execute(stmt)
                    db_run = res.scalar_one_or_none()
                    if not db_run:
                        db.add(PipelineRun(
                            repo_name=repo_full,
                            run_id=run_id,
                            installation_id=0,
                            status="pending",
                            branch=branch,
                            commit_sha=commit_sha,
                            run_url=url,
                            workflow_name=name or "Bitbucket Pipeline",
                            provider="bitbucket",
                        ))
                    else:
                        db_run.status = "pending"
                    await db.commit()
        except Exception as e:
            logger.error(f"DB Error: {e}")

        return {"status": "queued", "message": "Bitbucket failure queued"}

    return {"status": "ignored", "state": state}


@router.post("/gitlab", status_code=status.HTTP_202_ACCEPTED)
async def gitlab_webhook_handler(
    request: Request,
    x_gitlab_event: str | None = Header(None, alias="X-Gitlab-Event"),
    x_gitlab_token: str | None = Header(None, alias="X-Gitlab-Token")
):
    """Processes incoming GitLab webhook events."""
    logger.info(f"Received GitLab webhook event '{x_gitlab_event}'")

    # Simple token verification
    if settings.GITHUB_WEBHOOK_SECRET and x_gitlab_token != settings.GITHUB_WEBHOOK_SECRET:
        logger.warning("GitLab webhook token mismatch.")
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if x_gitlab_event != "Pipeline Hook":
        return {"status": "ignored", "event": x_gitlab_event}

    obj_attrs = payload.get("object_attributes", {})
    status_val = obj_attrs.get("status")
    
    project = payload.get("project", {})
    repo_name = project.get("path_with_namespace", "unknown")
    run_id = obj_attrs.get("id")
    branch = obj_attrs.get("ref")
    commit_sha = obj_attrs.get("sha")
    
    # Map GitLab to ops-pilot fields
    if status_val == "failed":
        logger.error(f"🚨 GitLab CI FAILURE DETECTED: Pipeline #{run_id} in {repo_name}. Queueing log scraper...")
        
        # Insert as pending
        try:
            async with async_session() as db:
                async with db.begin():
                    stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                    res = await db.execute(stmt)
                    db_run = res.scalar_one_or_none()
                    if not db_run:
                        db.add(PipelineRun(
                            repo_name=repo_name,
                            run_id=run_id,
                            status="pending",
                            branch=branch,
                            commit_sha=commit_sha,
                            workflow_name="GitLab Pipeline"
                        ))
                    else:
                        db_run.status = "pending"
                    await db.commit()
        except Exception as e:
            logger.error(f"DB Error: {e}")

        # Queue task
        task_payload = {
            "repo_name": repo_name,
            "run_id": run_id,
            "branch": branch,
            "commit_sha": commit_sha,
            "workflow_name": "GitLab Pipeline",
            "provider": "gitlab",
            "project_id": project.get("id")
        }
        await redis_queue.push_task("devops_pipeline_queue", task_payload)
        return {"status": "queued", "message": "GitLab failure queued"}

    return {"status": "ignored", "state": status_val}
