import asyncio
import logging
import signal
import sys
from datetime import datetime
from sqlalchemy.future import select
from app.core.database import async_session
from app.models.pipeline import PipelineRun
from app.models.audit_event import AuditEvent
from app.services.queue import redis_queue
from app.services.pipeline import pipeline_coordinator
from app.services.notifications import notifier
from app.services.llm import llm_service
from app.services.ticketing import jira_service

# Configure structured logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("worker")

QUEUE_NAME = "devops_pipeline_queue"

# Graceful shutdown flag
_shutdown_requested = False


def _handle_sigterm(signum, frame):
    global _shutdown_requested
    logger.info("SIGTERM received – finishing current task then shutting down...")
    _shutdown_requested = True


async def _write_audit(event_type: str, resource_id: str | None, detail: str) -> None:
    """Best-effort audit log write from worker."""
    try:
        async with async_session() as db:
            async with db.begin():
                db.add(AuditEvent(
                    event_type=event_type,
                    actor="worker",
                    resource_id=resource_id,
                    detail=detail,
                ))
    except Exception as exc:
        logger.error(f"Worker audit write failed: {exc}")


async def process_task(payload: dict):
    repo_name = payload.get("repo_name")
    run_id = payload.get("run_id")
    installation_id = payload.get("installation_id")
    branch = payload.get("branch")
    commit_sha = payload.get("commit_sha")
    pr_number = payload.get("pr_number")

    if not all([repo_name, run_id, installation_id]):
        logger.error(f"Invalid task payload received: {payload}")
        return

    logger.info(f"Processing task for run {run_id} in repository {repo_name}...")
    await _write_audit("worker.task.started", str(run_id), f"repo={repo_name} branch={branch}")

    db_run = None
    error_details = None

    try:
        async with async_session() as db:
            # Mark as processing
            async with db.begin():
                stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                result = await db.execute(stmt)
                db_run = result.scalar_one_or_none()

                if not db_run:
                    db_run = PipelineRun(
                        repo_name=repo_name,
                        run_id=run_id,
                        installation_id=installation_id,
                        status="processing",
                        branch=branch,
                        commit_sha=commit_sha,
                        run_url=payload.get("run_url"),
                        workflow_name=payload.get("workflow_name"),
                    )
                    db.add(db_run)
                else:
                    db_run.status = "processing"

                await db.commit()

            # Run the pipeline
            parsed_result = await pipeline_coordinator.process_failed_run(repo_name, run_id, installation_id)

            # --- LLM summarization ---
            llm_summary = None
            if parsed_result and "error" not in parsed_result:
                enriched = {**parsed_result, "repo_name": repo_name}
                llm_summary = await llm_service.summarize_failure(enriched)

            async with db.begin():
                stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                result = await db.execute(stmt)
                db_run = result.scalar_one_or_none()

                if not db_run:
                    logger.error(f"PipelineRun for run {run_id} disappeared from the database!")
                    return

                if not parsed_result or "error" in parsed_result:
                    db_run.status = "failed"
                    db_run.error_message = parsed_result.get("detail") if parsed_result else "Unknown pipeline error"
                    db_run.error_type = parsed_result.get("error") if parsed_result else "PipelineError"
                    error_details = None
                else:
                    db_run.status = "completed"
                    db_run.error_language = parsed_result.get("language")
                    db_run.error_filename = parsed_result.get("filename")
                    db_run.error_line_number = parsed_result.get("line_number")
                    db_run.error_type = parsed_result.get("error_type")
                    db_run.error_message = parsed_result.get("error_message")
                    db_run.error_traceback = parsed_result.get("traceback")
                    db_run.step_log_file = parsed_result.get("step_log_file")
                    db_run.llm_summary = llm_summary
                    error_details = parsed_result

                    # Flaky Test Tracking
                    if db_run.error_filename and db_run.error_type:
                        sig = f"{db_run.error_filename}:{db_run.error_line_number}:{db_run.error_type}"
                        from app.models.flaky_test import FlakyTest
                        # Find existing signature
                        stmt_flaky = select(FlakyTest).where(FlakyTest.error_signature == sig)
                        res_flaky = await db.execute(stmt_flaky)
                        flaky_record = res_flaky.scalar_one_or_none()
                        if not flaky_record:
                            flaky_record = FlakyTest(
                                repo_name=repo_name,
                                workflow_name=db_run.workflow_name or "unknown",
                                error_signature=sig,
                                failure_count=1,
                                success_count=0,
                                is_flaky=False
                            )
                            db.add(flaky_record)
                        else:
                            flaky_record.failure_count += 1
                            if flaky_record.success_count > 0:
                                flaky_record.is_flaky = True
                                db_run.is_flaky = True

                await db.commit()
                logger.info(f"Database updated for run {run_id}. Status: {db_run.status}")

        await _write_audit(
            f"worker.task.{db_run.status if db_run else 'unknown'}",
            str(run_id),
            f"repo={repo_name}"
        )

        # MTTR calculation
        if db_run and db_run.status == "completed" and db_run.created_at:
            now = datetime.utcnow()
            diff_min = (now - db_run.created_at).total_seconds() / 60.0
            db_run.mttr_minutes = round(diff_min, 1)

        await db.commit()

        # Send notifications
        try:
            await notifier.notify_all(repo_name, run_id, db_run.status if db_run else "unknown", error_details, installation_id, pr_number, branch)
        except Exception as e:
            logger.error(f"Failed to send external notifications for run {run_id}: {e}")

        # Ticketing (Jira)
        if db_run and db_run.status == "failed" and (branch in ("main", "master")):
            try:
                await jira_service.create_issue(
                    repo_name=repo_name,
                    run_id=run_id,
                    branch=branch,
                    error_type=db_run.error_type,
                    error_message=db_run.error_message,
                    llm_summary=db_run.llm_summary,
                    run_url=db_run.run_url,
                )
            except Exception as e:
                logger.error(f"Failed to create Jira ticket for run {run_id}: {e}")

    except Exception as e:
        logger.error(f"Error handling task for run {run_id}: {e}", exc_info=True)
        await _write_audit("worker.task.error", str(run_id), str(e))


async def main():
    logger.info("Starting Ops-Pilot Background Worker...")
    signal.signal(signal.SIGTERM, _handle_sigterm)

    while not _shutdown_requested:
        try:
            task = await redis_queue.pop_task(QUEUE_NAME, timeout=5)
            if task:
                await process_task(task)
        except asyncio.CancelledError:
            logger.info("Worker loop cancelled, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in worker main loop: {e}")
            await asyncio.sleep(2)  # Avoid tight spinning on consecutive exceptions

    logger.info("Worker shutdown complete.")
    await redis_queue.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt.")
