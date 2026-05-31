"""Routes synthesis to Anthropic or Ollama based on SYNTHESIS_BACKEND setting."""
import json
import logging

from agent.config import settings
from agent.synthesizer.prompts import SYNTHESIS_PROMPT

logger = logging.getLogger(__name__)


async def synthesize(name: str, company: str, role: str, raw_data: dict) -> dict:
    research_data = _flatten_research(raw_data)
    prompt = SYNTHESIS_PROMPT.format(
        name=name,
        company=company,
        role=role or "Unknown",
        research_data=research_data,
    )

    if settings.synthesis_backend == "ollama":
        return await _call_ollama(prompt)
    return await _call_anthropic(prompt)


async def _call_anthropic(prompt: str) -> dict:
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text
        return _parse_json(text)
    except Exception as e:
        logger.warning(f"Anthropic synthesis failed: {e}")
        return _fallback()


async def _call_ollama(prompt: str) -> dict:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            text = resp.json().get("response", "")
            return _parse_json(text)
    except Exception as e:
        logger.warning(f"Ollama synthesis failed: {e}")
        return _fallback()


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Synthesis returned invalid JSON")
        return _fallback()


def _flatten_research(raw: dict) -> str:
    parts = []
    for source, data in raw.items():
        if not data:
            continue
        parts.append(f"[{source.upper()}]")
        if isinstance(data, dict):
            summary = data.get("summary") or data.get("summary_text") or data.get("about_snippet", "")
            if summary:
                parts.append(f"Summary: {summary}")
            for k, v in data.items():
                if k in ("summary", "summary_text", "about_snippet"):
                    continue
                if isinstance(v, list) and v:
                    parts.append(f"{k}: {', '.join(str(i) for i in v[:3])}")
                elif isinstance(v, str) and v:
                    parts.append(f"{k}: {v[:200]}")
        parts.append("")
    return "\n".join(parts)


def _fallback() -> dict:
    return {
        "talking_points": [],
        "background_summary": "",
        "shared_interests": [],
        "outreach_hook": "",
        "caution": "",
    }
