import io
import zipfile
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.services.github_app import github_app_service
from app.services.log_parser import parse_log_text
from app.services.queue import redis_queue

logger = logging.getLogger("pipeline")

DEAD_LETTER_QUEUE = "devops_dead_letter_queue"


def _log_retry(retry_state):
    logger.warning(
        f"Retrying log download attempt {retry_state.attempt_number} "
        f"after error: {retry_state.outcome.exception()}"
    )


class DevOpsPipeline:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        before_sleep=_log_retry,
        reraise=True,
    )
    async def _download_logs_with_retry(
        self, repo_full_name: str, run_id: int, installation_id: int
    ) -> bytes:
        """Downloads workflow logs with automatic retry and exponential back-off."""
        return await github_app_service.download_workflow_logs(
            repo_full_name, run_id, installation_id
        )

    async def process_failed_run(
        self, repo_full_name: str, run_id: int, installation_id: int
    ) -> dict | None:
        """Downloads the workflow logs, parses them, and extracts the core error context.

        On permanent failure (after retries), pushes to the dead-letter queue.
        """
        logger.info(f"Starting log download and parse pipeline for run {run_id}...")

        try:
            logs_zip_bytes = await self._download_logs_with_retry(
                repo_full_name, run_id, installation_id
            )
        except Exception as e:
            logger.error(f"Pipeline permanently failed to download logs for run {run_id}: {e}")
            # Push to dead-letter queue for manual inspection
            try:
                await redis_queue.push_task(DEAD_LETTER_QUEUE, {
                    "repo_name": repo_full_name,
                    "run_id": run_id,
                    "installation_id": installation_id,
                    "error": "failed_to_download_logs",
                    "detail": str(e),
                })
                logger.info(f"Pushed failed run {run_id} to dead-letter queue.")
            except Exception as dlq_err:
                logger.error(f"Failed to push to dead-letter queue: {dlq_err}")

            return {
                "error": "failed_to_download_logs",
                "detail": str(e)
            }

        # Extract zip in-memory and parse logs
        try:
            with zipfile.ZipFile(io.BytesIO(logs_zip_bytes)) as archive:
                log_files = sorted(
                    [name for name in archive.namelist() if name.endswith(".txt")]
                )
                logger.info(f"Extracted zip contents. Found {len(log_files)} log step files.")

                for filename in log_files:
                    if "Post" in filename or "checkout" in filename:
                        continue

                    content = archive.read(filename).decode("utf-8", errors="ignore")
                    parsed_error = parse_log_text(content)
                    if parsed_error:
                        logger.info(f"Successfully scraped failure context from step log: '{filename}'")
                        parsed_error["step_log_file"] = filename
                        return parsed_error

            logger.warning(f"No error tracebacks were extracted from the logs of run {run_id}")
            return {
                "error": "no_traceback_detected",
                "detail": "Workflow run reported a failure, but log signatures did not match standard error regexes."
            }

        except Exception as e:
            logger.error(f"Pipeline failed to extract/parse logs: {e}")
            return {
                "error": "failed_to_parse_logs",
                "detail": str(e)
            }


pipeline_coordinator = DevOpsPipeline()
