import logging
import httpx
from app.core.config import settings
from app.services.github_app import github_app_service

logger = logging.getLogger("notifications")

class NotificationService:
    async def send_slack_notification(self, repo_name: str, run_id: int, status: str, error_details: dict | None) -> None:
        url = settings.SLACK_WEBHOOK_URL
        if not url:
            logger.debug("Slack webhook URL not configured. Skipping Slack notification.")
            return

        run_url = f"https://github.com/{repo_name}/actions/runs/{run_id}"
        
        # Build Slack Block layout
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Build Failure in {repo_name.split('/')[-1]}",
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

            # Truncate traceback if it's too long
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
            "title": f"🚨 CI Build Failure: {repo_name}",
            "url": run_url,
            "color": 15158332, # Dark Red
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
            f"### 🚨 CI Pipeline Failure Detected\n\n"
            f"**Error Type**: `{err_type}`\n"
            f"**Details**: {msg}\n\n"
            f"**🤖 AI Incident Summary & Suggested Fix**:\n"
            f"{summary}\n\n"
            f"---\n"
            f"*Generated automatically by Ops-Pilot*"
        )
        
        try:
            await github_app_service.create_pr_comment(repo_name, pr_number, installation_id, body)
        except Exception as e:
            logger.error(f"Failed to send PR comment: {e}")

    async def notify_all(self, repo_name: str, run_id: int, status: str, error_details: dict | None, installation_id: int | None = None, pr_number: int | None = None) -> None:
        import asyncio
        tasks = [
            self.send_slack_notification(repo_name, run_id, status, error_details),
            self.send_discord_notification(repo_name, run_id, status, error_details),
        ]
        if installation_id and pr_number:
            tasks.append(self.send_pr_comment(repo_name, pr_number, installation_id, status, error_details))
            
        await asyncio.gather(*tasks, return_exceptions=True)


notifier = NotificationService()
