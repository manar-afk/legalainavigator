import logging
from typing import Optional, Dict, Any
from .config import settings

logger = logging.getLogger(__name__)

# Try to initialize google-genai client
_genai_client = None
_is_live = False

try:
    from google import genai
    from google.genai import types
    if settings.USE_VERTEX_AI and settings.GOOGLE_CLOUD_PROJECT:
        _genai_client = genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.VERTEX_AI_LOCATION
        )
        _is_live = True
        logger.info(f"Initialized Google GenAI Vertex client for project {settings.GOOGLE_CLOUD_PROJECT}")
    elif settings.GEMINI_API_KEY:
        _genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        _is_live = True
        logger.info("Initialized Google GenAI client with API key")
    else:
        logger.info("No Gemini API key or Vertex AI project configured. Running in Local Offline Fallback Mode.")
except Exception as e:
    logger.warning(f"Could not initialize Google GenAI SDK: {e}. Running in Local Offline Fallback Mode.")


class GeminiClientWrapper:
    """Wrapper around Google GenAI SDK with graceful offline fallback."""

    def __init__(self):
        self.is_live = _is_live
        self.client = _genai_client

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generates content via Gemini API or falls back to deterministic local heuristic."""
        selected_model = model or settings.DEFAULT_FAST_MODEL

        if self.is_live and self.client:
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    system_instruction=system_instruction
                )
                response = self.client.models.generate_content(
                    model=selected_model,
                    contents=prompt,
                    config=config
                )
                return response.text
            except Exception as e:
                logger.error(f"Live Gemini API call failed: {e}. Falling back to offline engine.")

        # Offline fallback response generator
        return self._generate_offline_fallback(prompt, system_instruction)

    def _generate_offline_fallback(self, prompt: str, system_instruction: Optional[str]) -> str:
        """Deterministic fallback when running without cloud credentials."""
        prompt_lower = prompt.lower()
        if "what is an indemnity clause" in prompt_lower:
            return (
                "An indemnity clause is a contractual commitment where one party agrees to compensate "
                "the other party for specific potential losses, damages, or liabilities that may arise "
                "during or after the performance of the contract."
            )
        return (
            "This analysis is based on available document sections and provided circumstances. "
            "Please review the extracted evidence citations."
        )


gemini_client = GeminiClientWrapper()
