"""
LLM Service – AI-powered incident summarization.

Falls back gracefully when LLM_API_KEY is not configured or the call fails.
"""
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("services.llm")


class LLMService:
    async def summarize_failure(self, error_details: dict) -> str | None:
        """
        Calls the OpenAI Chat Completions API to produce a concise human-readable
        incident summary (2-3 sentences) from the parsed error details.

        Returns None if LLM_API_KEY is not set or the call fails.
        """
        if not settings.LLM_API_KEY:
            logger.debug("LLM_API_KEY not set – skipping AI incident summary.")
            return None

        error_type = error_details.get("error_type", "Unknown")
        error_message = error_details.get("error_message", "")
        filename = error_details.get("filename", "Unknown")
        line = error_details.get("line_number", "?")
        traceback = error_details.get("traceback", "")[:800]  # Truncate to save tokens
        language = error_details.get("language", "Unknown")
        repo_name = error_details.get("repo_name", "Unknown")

        prompt = (
            f"A CI/CD pipeline failed for the repository '{repo_name}'.\n\n"
            f"Error Type: {error_type}\n"
            f"Language: {language}\n"
            f"File: {filename} (line {line})\n"
            f"Error Message: {error_message}\n"
            f"Traceback snippet:\n{traceback}\n\n"
            "Write a concise 2-3 sentence incident summary suitable for a DevOps dashboard. "
            "Explain what failed, why it likely failed, and suggest a quick fix. "
            "Be direct and actionable."
        )

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.OPENAI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are an expert DevOps incident analyst."},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 200,
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                data = response.json()
                summary = data["choices"][0]["message"]["content"].strip()
                logger.info("LLM incident summary generated successfully.")
                return summary

        except Exception as exc:
            logger.error(f"LLM summarization failed: {exc}")
            return None


llm_service = LLMService()
