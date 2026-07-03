"""
Jira Ticketing Integration Service.

Automatically creates a high-priority Jira issue when a CI pipeline fails
on a protected branch (e.g., main/master).
"""
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("ticketing")


class JiraService:
    def _is_configured(self) -> bool:
        return all([
            settings.JIRA_BASE_URL,
            settings.JIRA_EMAIL,
            settings.JIRA_API_TOKEN,
            settings.JIRA_PROJECT_KEY,
        ])

    async def create_issue(
        self,
        repo_name: str,
        run_id: int,
        branch: str,
        error_type: str | None,
        error_message: str | None,
        llm_summary: str | None,
        run_url: str | None,
    ) -> str | None:
        """Creates a high-priority Jira bug ticket for a CI failure.
        
        Returns the created issue key (e.g. OPS-42) or None if not configured.
        """
        if not self._is_configured():
            logger.debug("Jira not configured – skipping ticket creation.")
            return None

        summary = f"[Ops-Pilot] CI Failure in {repo_name} on {branch} (Run #{run_id})"
        description = self._build_description(repo_name, run_id, branch, error_type, error_message, llm_summary, run_url)

        payload = {
            "fields": {
                "project": {"key": settings.JIRA_PROJECT_KEY},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High"},
                "labels": ["ops-pilot", "ci-failure", "automated"],
            }
        }

        auth = (settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)
        url = f"{settings.JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, auth=auth)
                response.raise_for_status()
                issue_key = response.json().get("key")
                logger.info(f"Jira ticket created: {issue_key} for run {run_id} in {repo_name}")
                return issue_key
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Jira API error creating ticket for run {run_id}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
            except Exception as e:
                logger.error(f"Failed to create Jira ticket for run {run_id}: {e}")
        return None

    def _build_description(
        self,
        repo_name: str,
        run_id: int,
        branch: str,
        error_type: str | None,
        error_message: str | None,
        llm_summary: str | None,
        run_url: str | None,
    ) -> str:
        parts = [
            "CI pipeline failure detected by Ops-Pilot.",
            "",
            f"Repository: {repo_name}",
            f"Branch: {branch}",
            f"GitHub Actions Run: {run_url or 'N/A'} (#{run_id})",
            "",
            "--- Error Details ---",
            f"Type: {error_type or 'Unknown'}",
            f"Message: {error_message or 'No details available'}",
        ]
        if llm_summary:
            parts += [
                "",
                "--- AI Incident Summary ---",
                llm_summary,
            ]
        parts += ["", "Created automatically by Ops-Pilot."]
        return "\n".join(parts)


jira_service = JiraService()
