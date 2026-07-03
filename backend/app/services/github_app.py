import time
import logging
import jwt
import httpx
from app.core.config import settings

logger = logging.getLogger("github_app")

class GitHubAppService:
    def __init__(self):
        self.api_url = "https://api.github.com"

    def get_jwt(self) -> str:
        """Generates a JSON Web Token (JWT) signed with the App's private key.
        
        This JWT is used to authenticate requests to GitHub App management APIs
        and to request installation-specific access tokens.
        """
        now = int(time.time())
        # Subtract 60 seconds to allow for clock drift between local machine and GitHub servers
        payload = {
            "iat": now - 60,
            "exp": now + (9 * 60),  # Expires in 9 minutes (max is 10)
            "iss": str(settings.GITHUB_APP_ID),
        }
        
        private_key = settings.formatted_private_key
        try:
            jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
            return jwt_token
        except Exception as e:
            logger.error(f"Failed to generate GitHub App JWT: {e}")
            raise

    async def get_installation_access_token(self, installation_id: int) -> str:
        """Requests a temporary access token for a specific repository installation."""
        jwt_token = self.get_jwt()
        url = f"{self.api_url}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["token"]
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error negotiating installation token for installation {installation_id}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
                raise
            except Exception as e:
                logger.error(f"Error negotiating installation token: {e}")
                raise

    async def download_workflow_logs(self, repo_full_name: str, run_id: int, installation_id: int) -> bytes:
        """Downloads the zip archive of workflow logs for the specified run ID."""
        token = await self.get_installation_access_token(installation_id)
        url = f"{self.api_url}/repos/{repo_full_name}/actions/runs/{run_id}/logs"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Follow redirects is True because GitHub redirects us to a temporary AWS S3 pre-signed URL
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                logger.info(f"Requesting logs for run {run_id} in {repo_full_name}")
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.content
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error downloading workflow logs for run {run_id}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
                raise
            except Exception as e:
                logger.error(f"Error downloading workflow logs for run {run_id}: {e}")
                raise

    async def create_pr_comment(self, repo_full_name: str, pr_number: int, installation_id: int, body: str) -> None:
        """Creates a comment on a GitHub Pull Request."""
        token = await self.get_installation_access_token(installation_id)
        url = f"{self.api_url}/repos/{repo_full_name}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Creating PR comment on {repo_full_name}#{pr_number}")
                response = await client.post(url, headers=headers, json={"body": body})
                response.raise_for_status()
                logger.info(f"Successfully posted PR comment on {repo_full_name}#{pr_number}")
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error creating PR comment on {repo_full_name}#{pr_number}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
                raise
            except Exception as e:
                logger.error(f"Error creating PR comment on {repo_full_name}#{pr_number}: {e}")
                raise

github_app_service = GitHubAppService()
