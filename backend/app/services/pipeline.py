import io
import zipfile
import logging
from app.services.github_app import github_app_service
from app.services.log_parser import parse_log_text

logger = logging.getLogger("pipeline")

class DevOpsPipeline:
    async def process_failed_run(
        self, repo_full_name: str, run_id: int, installation_id: int
    ) -> dict | None:
        """Downloads the workflow logs, parses them, and extracts the core error context."""
        logger.info(f"Starting log download and parse pipeline for run {run_id}...")
        
        try:
            # 1. Download logs zip
            logs_zip_bytes = await github_app_service.download_workflow_logs(
                repo_full_name, run_id, installation_id
            )
        except Exception as e:
            logger.error(f"Pipeline failed to download logs for run {run_id}: {e}")
            return {
                "error": "failed_to_download_logs",
                "detail": str(e)
            }

        # 2. Extract zip in-memory and parse logs
        try:
            with zipfile.ZipFile(io.BytesIO(logs_zip_bytes)) as archive:
                # Get all files and sort them. Step log files are usually organized by folder (job)
                # and prefixed with numbers (e.g. "build/1_setup.txt", "build/2_test.txt")
                log_files = sorted(
                    [name for name in archive.namelist() if name.endswith(".txt")]
                )
                
                logger.info(f"Extracted zip contents. Found {len(log_files)} log step files.")

                # Scan files starting from the last step (or in chronological order)
                # Scanning in reverse order can find the final error quicker, 
                # but standard chronological order ensures we capture the first failure that stopped the build.
                for filename in log_files:
                    # Ignore setup/teardown steps if they pass, focusing on test/build logs
                    if "Post" in filename or "checkout" in filename:
                        continue
                        
                    content = archive.read(filename).decode("utf-8", errors="ignore")
                    
                    # Try to parse failure tracebacks
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
