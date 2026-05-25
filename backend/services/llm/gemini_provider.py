import json
import os
import time
from typing import Any, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import Settings
from backend.core.logging import get_logger
from backend.services.llm.base_llm import (
    BaseLLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMTransientError,
    LLMValidationError,
)

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def pydantic_to_gemini_schema(schema: dict, defs: dict | None = None) -> dict:
    """
    Recursively translate a standard Pydantic JSON schema (OpenAPI style)
    to the uppercase types and structure expected by Google Gemini REST API.
    """
    if defs is None:
        defs = schema.get("$defs", schema.get("definitions", {}))

    if not isinstance(schema, dict):
        return {}

    # Resolve reference
    if "$ref" in schema:
        ref_path = schema["$ref"]
        ref_name = ref_path.split("/")[-1]
        ref_schema = defs.get(ref_name, {})
        return pydantic_to_gemini_schema(ref_schema, defs)

    # Handle anyOf / oneOf (commonly generated for Union or Optional fields)
    if "anyOf" in schema or "oneOf" in schema:
        options = schema.get("anyOf", schema.get("oneOf", []))
        nullable = False
        non_null_options = []
        for opt in options:
            if isinstance(opt, dict) and "$ref" in opt:
                opt = pydantic_to_gemini_schema(opt, defs)

            if isinstance(opt, dict):
                if opt.get("type") in ("null", "NULL"):
                    nullable = True
                else:
                    non_null_options.append(opt)

        if non_null_options:
            # Recursively convert the first non-null type as the base schema
            base_schema = pydantic_to_gemini_schema(non_null_options[0], defs)
            if nullable:
                base_schema["nullable"] = True
            return base_schema
        else:
            return {"type": "STRING", "nullable": True}

    gemini_schema = {}

    # Translate type to uppercase
    json_type = schema.get("type")
    if json_type:
        if isinstance(json_type, list):
            nullable = "null" in json_type
            main_types = [t for t in json_type if t != "null"]
            if main_types:
                gemini_schema["type"] = main_types[0].upper()
            else:
                gemini_schema["type"] = "STRING"
            if nullable:
                gemini_schema["nullable"] = True
        else:
            type_str = str(json_type).upper()
            # Map common types
            if type_str == "NUMBER":
                gemini_schema["type"] = "NUMBER"
            elif type_str == "INTEGER":
                gemini_schema["type"] = "INTEGER"
            elif type_str == "STRING":
                gemini_schema["type"] = "STRING"
            elif type_str == "BOOLEAN":
                gemini_schema["type"] = "BOOLEAN"
            elif type_str == "OBJECT":
                gemini_schema["type"] = "OBJECT"
            elif type_str == "ARRAY":
                gemini_schema["type"] = "ARRAY"
            else:
                gemini_schema["type"] = type_str
    else:
        # Fallback to OBJECT if properties are defined, ARRAY if items are defined
        if "properties" in schema:
            gemini_schema["type"] = "OBJECT"
        elif "items" in schema:
            gemini_schema["type"] = "ARRAY"

    # Copy basic metadata
    if "description" in schema:
        gemini_schema["description"] = schema["description"]
    if "enum" in schema:
        gemini_schema["enum"] = [str(e) for e in schema["enum"]]

    # Translate array items
    if "items" in schema:
        gemini_schema["items"] = pydantic_to_gemini_schema(schema["items"], defs)

    # Translate object properties
    if "properties" in schema:
        gemini_schema["properties"] = {
            k: pydantic_to_gemini_schema(v, defs)
            for k, v in schema["properties"].items()
        }

    if "required" in schema:
        gemini_schema["required"] = schema["required"]

    return gemini_schema


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider implementation."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        model: str | None = None,
    ) -> None:
        """
        Initialize the Gemini Provider.

        Args:
            settings: Application settings.
            client: Optional httpx.AsyncClient to reuse.
            model: Optional model override (falls back to settings.llm_model).
        """
        super().__init__(settings)

        self._api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
        if not self._api_key:
            raise LLMProviderError(
                "Google API key is not configured. Please set GOOGLE_API_KEY."
            )

        # Fallback to gemini-1.5-flash if the settings model is not a Gemini model
        configured_model = model or settings.llm_model
        if "gemini" not in configured_model.lower():
            logger.warning(
                "Configured model '%s' is not a Gemini model. Defaulting to 'gemini-1.5-flash'.",
                configured_model,
            )
            self._model = "gemini-1.5-flash"
        else:
            self._model = configured_model

        self._client = client
        self._own_client = False
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.http_timeout_seconds),
                follow_redirects=True,
            )
            self._own_client = True

    async def close(self) -> None:
        """Close the internal HTTP client if owned by this provider."""
        if self._own_client and self._client:
            await self._client.aclose()

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        response_schema: Type[T] | None = None,
        timeout: float | None = None,
    ) -> str | T:
        """
        Generate content using the Google Gemini REST API.
        """
        start_time = time.perf_counter()

        # Build payload
        contents = [{"parts": [{"text": prompt}]}]
        payload: dict[str, Any] = {"contents": contents}

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        generation_config: dict[str, Any] = {"temperature": temperature}

        if response_schema is not None:
            generation_config["responseMimeType"] = "application/json"
            raw_schema = response_schema.model_json_schema()
            generation_config["responseSchema"] = pydantic_to_gemini_schema(raw_schema)

        payload["generationConfig"] = generation_config

        # Build endpoint URL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        params = {"key": self._api_key}
        headers = {"Content-Type": "application/json"}

        # Custom timeout or fallback
        request_timeout = timeout or self._settings.http_timeout_seconds

        attempt_settings = self._settings

        @retry(
            reraise=True,
            stop=stop_after_attempt(attempt_settings.http_max_retries),
            wait=wait_exponential(
                multiplier=attempt_settings.http_retry_backoff_seconds,
                min=attempt_settings.http_retry_backoff_seconds,
                max=30.0,
            ),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.NetworkError, LLMTransientError, LLMRateLimitError)
            ),
        )
        async def _execute_request() -> dict[str, Any]:
            try:
                response = await self._client.post(
                    url,
                    json=payload,
                    params=params,
                    headers=headers,
                    timeout=httpx.Timeout(request_timeout),
                )
            except httpx.TimeoutException as exc:
                logger.warning("provider=gemini model=%s timeout", self._model)
                raise LLMTransientError("Gemini request timed out") from exc
            except httpx.NetworkError as exc:
                logger.warning("provider=gemini model=%s network_error", self._model)
                raise LLMTransientError("Gemini network error occurred") from exc

            if response.status_code == 429:
                logger.warning("provider=gemini model=%s rate_limit (429)", self._model)
                raise LLMRateLimitError("Gemini rate limit exceeded")

            if response.status_code >= 500:
                logger.warning(
                    "provider=gemini model=%s upstream_error status=%d",
                    self._model,
                    response.status_code,
                )
                raise LLMTransientError(
                    f"Gemini server error: {response.text}",
                    details={"status_code": response.status_code},
                )

            if response.status_code >= 400:
                logger.error(
                    "provider=gemini model=%s client_error status=%d body=%s",
                    self._model,
                    response.status_code,
                    response.text[:500],
                )
                raise LLMProviderError(
                    f"Gemini client request failed: {response.text}",
                    details={"status_code": response.status_code},
                )

            try:
                return response.json()
            except ValueError as exc:
                raise LLMProviderError(
                    "Gemini API returned invalid JSON",
                    details={"response_text": response.text[:500]},
                ) from exc

        try:
            data = await _execute_request()
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "provider=gemini model=%s success=False latency_ms=%.2f error=%s",
                self._model,
                elapsed_ms,
                exc,
            )
            raise

        # Process response candidates
        candidates = data.get("candidates", [])
        if not candidates:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "provider=gemini model=%s success=False latency_ms=%.2f error=no_candidates",
                self._model,
                elapsed_ms,
            )
            raise LLMProviderError("Gemini API returned no candidates", details={"response": data})

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            finish_reason = candidate.get("finishReason")
            prompt_feedback = data.get("promptFeedback", {})
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "provider=gemini model=%s success=False latency_ms=%.2f finish_reason=%s error=empty_parts",
                self._model,
                elapsed_ms,
                finish_reason,
            )
            raise LLMProviderError(
                f"Gemini API returned empty parts. Finish reason: {finish_reason}",
                details={"finish_reason": finish_reason, "prompt_feedback": prompt_feedback},
            )

        text = parts[0].get("text", "")
        if not text:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "provider=gemini model=%s success=False latency_ms=%.2f error=empty_text",
                self._model,
                elapsed_ms,
            )
            raise LLMProviderError("Gemini API returned empty text in candidate content parts")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "provider=gemini model=%s success=True latency_ms=%.2f",
            self._model,
            elapsed_ms,
        )

        if response_schema is not None:
            try:
                # Parse to ensure it is valid JSON first
                parsed_json = json.loads(text)
                return response_schema.model_validate(parsed_json)
            except json.JSONDecodeError as exc:
                logger.error(
                    "provider=gemini model=%s response_validation_failed error=json_decode_error text=%s",
                    self._model,
                    text[:500],
                )
                raise LLMValidationError(
                    "Failed to decode Gemini response as JSON",
                    details={"raw_text": text},
                ) from exc
            except ValidationError as exc:
                logger.error(
                    "provider=gemini model=%s response_validation_failed error=pydantic_validation",
                    self._model,
                )
                raise LLMValidationError(
                    "Gemini response did not match the expected schema",
                    details={"validation_errors": exc.errors(), "raw_text": text},
                ) from exc

        return text
