import asyncio
import logging
import sys
from sqlalchemy.future import select
from app.core.database import async_session
from app.models.pipeline import PipelineRun
from app.services.queue import redis_queue
from app.services.pipeline import pipeline_coordinator
from app.services.notifications import notifier

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("worker")

QUEUE_NAME = "devops_pipeline_queue"

async def process_task(payload: dict):
    repo_name = payload.get("repo_name")
    run_id = payload.get("run_id")
    installation_id = payload.get("installation_id")

    if not all([repo_name, run_id, installation_id]):
        logger.error(f"Invalid task payload received: {payload}")
        return

    logger.info(f"Processing task for run {run_id} in repository {repo_name}...")

    try:
        async with async_session() as db:
            # Check if PipelineRun already exists in DB
            async with db.begin():
                stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                result = await db.execute(stmt)
                db_run = result.scalar_one_or_none()

                if not db_run:
                    db_run = PipelineRun(
                        repo_name=repo_name,
                        run_id=run_id,
                        installation_id=installation_id,
                        status="processing"
                    )
                    db.add(db_run)
                else:
                    db_run.status = "processing"
                
                await db.commit()

            # Run the pipeline processing (downloads, parses logs)
            # Note: pipeline_coordinator.process_failed_run handles its own exceptions internally
            parsed_result = await pipeline_coordinator.process_failed_run(repo_name, run_id, installation_id)

            async with db.begin():
                # Reload db_run
                stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                result = await db.execute(stmt)
                db_run = result.scalar_one_or_none()

                if not db_run:
                    logger.error(f"PipelineRun for run {run_id} disappeared from the database!")
                    return

                if not parsed_result or "error" in parsed_result:
                    db_run.status = "failed"
                    # If we couldn't parse logs, we store the detail in traceback or msg
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
                    error_details = parsed_result

                await db.commit()
                logger.info(f"Database updated for run {run_id}. Status: {db_run.status}")

        # Send external notifications (Slack/Discord Webhooks)
        try:
            await notifier.notify_all(repo_name, run_id, db_run.status, error_details)
        except Exception as e:
            logger.error(f"Failed to send external notifications for run {run_id}: {e}")

    except Exception as e:
        logger.error(f"Error handling task for run {run_id}: {e}", exc_info=True)

async def main():
    logger.info("Starting Ops-Pilot Background Worker...")
    
    # Simple loop to fetch tasks from Redis
    while True:
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

    await redis_queue.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt.")
