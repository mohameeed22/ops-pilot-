import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("teams_notifier")


class TeamsNotifier:
    async def send_notification(self, repo_name: str, run_id: int, status: str, error_details: dict | None) -> None:
        url = settings.TEAMS_WEBHOOK_URL
        if not url:
            logger.debug("TEAMS_WEBHOOK_URL not set – skipping Teams.")
            return

        error_type = error_details.get("error_type", "Unknown") if error_details else "Unknown"
        error_msg = error_details.get("error_message", "No details") if error_details else "No details"

        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"CI Failure: {repo_name} Run #{run_id}",
            "title": f"CI Pipeline Failure: {repo_name}",
            "sections": [
                {
                    "activityTitle": f"Run #{run_id} in {repo_name}",
                    "facts": [
                        {"name": "Status", "value": status},
                        {"name": "Error Type", "value": error_type},
                        {"name": "Error Message", "value": error_msg},
                    ],
                    "potentialAction": [
                        {
                            "@type": "OpenUri",
                            "name": "View Run",
                            "targets": [{"os": "default", "uri": f"https://github.com/{repo_name}/actions/runs/{run_id}"}],
                        }
                    ],
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                logger.info("Teams notification sent successfully.")
            except Exception as e:
                logger.error(f"Teams notification failed: {e}")


teams_notifier = TeamsNotifier()
