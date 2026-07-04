import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("pagerduty_notifier")


class PagerDutyNotifier:
    async def trigger_incident(self, repo_name: str, run_id: int, error_details: dict | None) -> None:
        routing_key = settings.PAGERDUTY_ROUTING_KEY
        if not routing_key:
            logger.debug("PAGERDUTY_ROUTING_KEY not set – skipping PagerDuty.")
            return

        error_type = error_details.get("error_type", "Unknown") if error_details else "Unknown"
        error_msg = error_details.get("error_message", "No details") if error_details else "No details"

        payload = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"[Ops-Pilot] CI Failure: {repo_name} Run #{run_id} - {error_type}",
                "source": repo_name,
                "severity": "critical",
                "custom_details": {
                    "run_id": run_id,
                    "repo": repo_name,
                    "error_type": error_type,
                    "error_message": error_msg,
                    "run_url": f"https://github.com/{repo_name}/actions/runs/{run_id}",
                },
            },
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(settings.PAGERDUTY_API_URL, json=payload)
                resp.raise_for_status()
                logger.info(f"PagerDuty incident triggered for run {run_id}")
            except Exception as e:
                logger.error(f"PagerDuty trigger failed: {e}")

    async def resolve_incident(self, repo_name: str, run_id: int, dedup_key: str) -> None:
        routing_key = settings.PAGERDUTY_ROUTING_KEY
        if not routing_key:
            return
        payload = {
            "routing_key": routing_key,
            "event_action": "resolve",
            "dedup_key": dedup_key,
        }
        async with httpx.AsyncClient() as client:
            try:
                await client.post(settings.PAGERDUTY_API_URL, json=payload)
            except Exception as e:
                logger.error(f"PagerDuty resolve failed: {e}")


pagerduty_notifier = PagerDutyNotifier()
