import logging
import httpx
import re
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import async_session
from app.services.github_app import github_app_service
from app.services.email_notifier import email_notifier
from app.services.pagerduty_notifier import pagerduty_notifier
from app.services.teams_notifier import teams_notifier

logger = logging.getLogger("notifications")


async def _match_rule(rule, repo_name: str, branch: str | None, status: str) -> bool:
    if rule.repo_pattern and not re.search(rule.repo_pattern, repo_name):
        return False
    if rule.branch_pattern and (not branch or not re.search(rule.branch_pattern, branch)):
        return False
    if rule.status_filter and rule.status_filter != status:
        return False
    return True


async def get_channels_for(repo_name: str, branch: str | None, status: str) -> set[str]:
    channels = {"slack", "discord"}
    try:
        async with async_session() as db:
            result = await db.execute(
                select(__import__("app.models.notification_rule", fromlist=["NotificationRule"]).NotificationRule)
                .where(__import__("app.models.notification_rule", fromlist=["NotificationRule"]).NotificationRule.is_active.is_(True))
            )
            rules = result.scalars().all()
            for rule in rules:
                if await _match_rule(rule, repo_name, branch, status):
                    channels.update(rule.channels.split(","))
    except Exception as e:
        logger.error(f"Failed to load notification rules: {e}")
    return channels


class NotificationService:
    async def send_slack_notification(self, repo_name: str, run_id: int, status: str, error_details: dict | None) -> None:
        url = settings.SLACK_WEBHOOK_URL
        if not url:
            logger.debug("Slack webhook URL not configured. Skipping Slack notification.")
            return

        run_url = f"https://github.com/{repo_name}/actions/runs/{run_id}"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"CI Build Failure in {repo_name.split('/')[-1]}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Repository:* `{repo_name}`\n*Run Link:* <{run_url}|Workflow Run #{run_id}>"
                }
            }
        ]

        if error_details:
            lang = error_details.get("language", "Unknown")
            err_type = error_details.get("error_type", "Unknown")
            filename = error_details.get("filename", "Unknown")
            line = error_details.get("line_number", "?")
            msg = error_details.get("error_message", "No message details.")
            tb = error_details.get("traceback", "")
            step_file = error_details.get("step_log_file", "Unknown")

            if len(tb) > 1500:
                tb = tb[:1500] + "\n... [truncated]"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Error:* `{err_type}`\n"
                        f"*Message:* {msg}\n"
                        f"*Location:* `{filename}` (Line {line})\n"
                        f"*Log Step:* `{step_file}`"
                    )
                }
            })

            if tb:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Traceback Snippet:*\n```{lang}\n{tb}\n```"
                    }
                })
        else:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_No error tracebacks could be parsed from the build logs._"
                }
            })

        payload = {"blocks": blocks}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("Slack notification sent successfully.")
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")

    async def send_discord_notification(self, repo_name: str, run_id: int, status: str, error_details: dict | None) -> None:
        url = settings.DISCORD_WEBHOOK_URL
        if not url:
            logger.debug("Discord webhook URL not configured. Skipping Discord notification.")
            return

        run_url = f"https://github.com/{repo_name}/actions/runs/{run_id}"

        embed = {
            "title": f"CI Build Failure: {repo_name}",
            "url": run_url,
            "color": 15158332,
            "fields": [
                {
                    "name": "Workflow Run",
                    "value": f"[#{run_id}]({run_url})",
                    "inline": True
                }
            ]
        }

        if error_details:
            lang = error_details.get("language", "Unknown")
            err_type = error_details.get("error_type", "Unknown")
            filename = error_details.get("filename", "Unknown")
            line = error_details.get("line_number", "?")
            msg = error_details.get("error_message", "No message details.")
            tb = error_details.get("traceback", "")
            step_file = error_details.get("step_log_file", "Unknown")

            embed["fields"].append({
                "name": "Location",
                "value": f"`{filename}:{line}` ({lang})",
                "inline": True
            })
            embed["fields"].append({
                "name": "Step Log File",
                "value": f"`{step_file}`",
                "inline": True
            })
            embed["fields"].append({
                "name": "Error Details",
                "value": f"**{err_type}**: {msg}",
                "inline": False
            })

            if tb:
                if len(tb) > 1000:
                    tb = tb[:1000] + "\n... [truncated]"
                embed["fields"].append({
                    "name": "Traceback Snippet",
                    "value": f"```{lang}\n{tb}\n```",
                    "inline": False
                })
        else:
            embed["description"] = "No error tracebacks could be parsed from the build logs."

        payload = {"embeds": [embed]}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("Discord notification sent successfully.")
            except Exception as e:
                logger.error(f"Failed to send Discord notification: {e}")

    async def send_pr_comment(self, repo_name: str, pr_number: int, installation_id: int, status: str, error_details: dict | None) -> None:
        if status != "failed" or not error_details:
            return

        err_type = error_details.get("error_type", "Unknown")
        msg = error_details.get("error_message", "No message details.")
        summary = error_details.get("llm_summary", "No AI summary generated.")

        body = (
            f"### CI Pipeline Failure Detected\n\n"
            f"**Error Type**: `{err_type}`\n"
            f"**Details**: {msg}\n\n"
            f"**AI Incident Summary & Suggested Fix**:\n"
            f"{summary}\n\n"
            f"---\n"
            f"*Generated automatically by Ops-Pilot*"
        )

        try:
            await github_app_service.create_pr_comment(repo_name, pr_number, installation_id, body)
        except Exception as e:
            logger.error(f"Failed to send PR comment: {e}")

    async def notify_all(self, repo_name: str, run_id: int, status: str, error_details: dict | None, installation_id: int | None = None, pr_number: int | None = None, branch: str | None = None) -> None:
        import asyncio

        channels = await get_channels_for(repo_name, branch, status)

        tasks = []
        if "slack" in channels:
            tasks.append(self.send_slack_notification(repo_name, run_id, status, error_details))
        if "discord" in channels:
            tasks.append(self.send_discord_notification(repo_name, run_id, status, error_details))
        if "teams" in channels:
            tasks.append(teams_notifier.send_notification(repo_name, run_id, status, error_details))
        if "email" in channels:
            tasks.append(email_notifier.notify_failure(repo_name, run_id, status, error_details))
        if "pagerduty" in channels and status == "failed":
            tasks.append(pagerduty_notifier.trigger_incident(repo_name, run_id, error_details))
        if installation_id and pr_number and "pr_comment" in channels:
            tasks.append(self.send_pr_comment(repo_name, pr_number, installation_id, status, error_details))

        await asyncio.gather(*tasks, return_exceptions=True)


notifier = NotificationService()
