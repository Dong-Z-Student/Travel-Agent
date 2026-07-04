from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx
from pydantic import BaseModel

from app.agent.json_parser import AgentJsonParseError, parse_pydantic_json
from app.agent.prompts import AGENT_SYSTEM_PROMPT, build_json_retry_prompt
from app.agent.schemas import ModelCallResult, ModelRole, StructuredModelResult, TokenUsage
from app.core.config import settings


class AgentModelConfigError(RuntimeError):
    pass


class AgentModelCallError(RuntimeError):
    pass


class AgentModelClient:
    def __init__(self) -> None:
        if not settings.deepseek_api_key:
            raise AgentModelConfigError("DEEPSEEK_API_KEY is not configured")

    @staticmethod
    def is_langchain_available() -> bool:
        try:
            import langchain_core  # noqa: F401
            import langchain_openai  # noqa: F401
        except ImportError:
            return False
        return True

    def invoke(
        self,
        messages: Sequence[dict[str, str]],
        *,
        model_role: ModelRole = "fast",
        temperature: float = 0.2,
    ) -> ModelCallResult:
        if not self.is_langchain_available():
            return self._invoke_http(messages, model_role=model_role, temperature=temperature)

        chat = self._build_chat(model_role=model_role, temperature=temperature)
        lc_messages = self._to_langchain_messages(messages)
        try:
            response = chat.invoke(lc_messages)
        except Exception as exc:
            raise AgentModelCallError(str(exc)) from exc

        content = response.content
        if isinstance(content, list):
            content = "".join(str(item) for item in content)

        return ModelCallResult(
            model=self._model_name(model_role),
            model_role=model_role,
            content=str(content or ""),
            token_usage=self._extract_token_usage(response),
            raw_metadata=dict(getattr(response, "response_metadata", {}) or {}),
        )

    def invoke_json(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        system_prompt: str = AGENT_SYSTEM_PROMPT,
        model_role: ModelRole = "fast",
        temperature: float = 0.1,
        fallback_to_planner: bool = True,
    ) -> StructuredModelResult:
        attempts = 0
        last_error: Exception | None = None
        roles: list[ModelRole] = [model_role]
        if fallback_to_planner and model_role == "fast":
            roles.append("planner")

        current_prompt = prompt
        for index, role in enumerate(roles):
            for _ in range(settings.agent_max_retries + 1):
                attempts += 1
                result = self.invoke(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": current_prompt},
                    ],
                    model_role=role,
                    temperature=temperature,
                )
                try:
                    parsed_model = parse_pydantic_json(result.content, schema)
                    return StructuredModelResult(
                        model=result.model,
                        model_role=role,
                        parsed=parsed_model.model_dump(),
                        content=result.content,
                        token_usage=result.token_usage,
                        attempts=attempts,
                        fallback_used=index > 0,
                    )
                except AgentJsonParseError as exc:
                    last_error = exc
                    current_prompt = build_json_retry_prompt(prompt, str(exc))

        raise AgentModelCallError(f"model JSON output could not be validated: {last_error}")

    def _build_chat(self, *, model_role: ModelRole, temperature: float):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise AgentModelConfigError(
                "LangChain dependencies are not installed. Run: pip install -r backend/requirements.txt"
            ) from exc

        return ChatOpenAI(
            model=self._model_name(model_role),
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=settings.agent_timeout_seconds,
            max_retries=settings.agent_max_retries,
            temperature=temperature,
        )

    def _invoke_http(
        self,
        messages: Sequence[dict[str, str]],
        *,
        model_role: ModelRole,
        temperature: float,
    ) -> ModelCallResult:
        url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self._model_name(model_role),
            "messages": list(messages),
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=settings.agent_timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentModelCallError(str(exc)) from exc

        choices = data.get("choices") or []
        if not choices:
            raise AgentModelCallError("DeepSeek response does not contain choices")
        message = choices[0].get("message") or {}
        usage = data.get("usage") or {}
        return ModelCallResult(
            model=self._model_name(model_role),
            model_role=model_role,
            content=str(message.get("content") or ""),
            token_usage=TokenUsage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                raw=dict(usage),
            ) if usage else None,
            raw_metadata={"transport": "httpx", "id": data.get("id")},
        )

    def _model_name(self, model_role: ModelRole) -> str:
        if model_role == "planner":
            return settings.deepseek_planner_model or settings.agent_complex_model
        return settings.deepseek_fast_model or settings.agent_default_model

    def _to_langchain_messages(self, messages: Sequence[dict[str, str]]):
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        mapped = []
        for item in messages:
            role = item.get("role")
            content = item.get("content") or ""
            if role == "system":
                mapped.append(SystemMessage(content=content))
            elif role == "assistant":
                mapped.append(AIMessage(content=content))
            else:
                mapped.append(HumanMessage(content=content))
        return mapped

    def _extract_token_usage(self, response: Any) -> TokenUsage | None:
        usage = getattr(response, "usage_metadata", None)
        metadata = getattr(response, "response_metadata", {}) or {}
        raw_usage = metadata.get("token_usage") or metadata.get("usage") or {}

        if usage:
            return TokenUsage(
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
                total_tokens=usage.get("total_tokens"),
                raw=dict(raw_usage),
            )
        if raw_usage:
            return TokenUsage(
                input_tokens=raw_usage.get("prompt_tokens"),
                output_tokens=raw_usage.get("completion_tokens"),
                total_tokens=raw_usage.get("total_tokens"),
                raw=dict(raw_usage),
            )
        return None


def get_model_status() -> dict[str, Any]:
    return {
        "configured": bool(settings.deepseek_api_key),
        "agent_mode": settings.agent_mode,
        "fast_model": settings.deepseek_fast_model,
        "planner_model": settings.deepseek_planner_model,
        "default_model": settings.agent_default_model,
        "complex_model": settings.agent_complex_model,
        "base_url": settings.deepseek_base_url,
        "timeout_seconds": settings.agent_timeout_seconds,
        "max_retries": settings.agent_max_retries,
        "langchain_available": AgentModelClient.is_langchain_available(),
    }
