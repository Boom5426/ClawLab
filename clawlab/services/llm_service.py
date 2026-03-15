from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from clawlab.core.models import LlmSettings


def get_llm_settings(config) -> LlmSettings:
    return config.llm


def _module_flag(settings: LlmSettings, module_name: str) -> bool:
    return {
        "materials": settings.use_llm_for_materials,
        "drafts": settings.use_llm_for_drafts,
        "learning": settings.use_llm_for_learning,
    }[module_name]


def get_llm_runtime_status(settings: LlmSettings, module_name: str | None = None) -> tuple[bool, str]:
    if settings.mode == "local":
        return False, "local mode enabled"
    if settings.provider == "none":
        return False, "provider is none"
    if module_name and not _module_flag(settings, module_name):
        return False, f"LLM disabled for {module_name}"
    if settings.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        return False, "OPENAI_API_KEY is missing"
    if settings.provider != "openai":
        return False, f"provider {settings.provider} is not supported"
    return True, "enabled"


def is_llm_enabled(settings: LlmSettings, module_name: str | None = None) -> bool:
    return get_llm_runtime_status(settings, module_name)[0]


def call_llm(
    *,
    settings: LlmSettings,
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> str:
    enabled, reason = get_llm_runtime_status(settings)
    if not enabled:
        raise RuntimeError(f"LLM is not available: {reason}")

    payload = {
        "model": settings.model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [],
    }
    if system_prompt:
        payload["messages"].append({"role": "system", "content": system_prompt})
    payload["messages"].append({"role": "user", "content": prompt})

    request = urllib.request.Request(
        url=f"{settings.openai_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise RuntimeError(f"LLM request failed: {error}") from error

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("LLM response did not contain a usable message content") from error
