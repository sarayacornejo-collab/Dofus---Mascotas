"""Llama a Claude para sintetizar las tendencias en propuestas + secciones editoriales.

Usa Anthropic SDK con:
- Modelo claude-opus-4-7 (override vía CLAUDE_MODEL).
- Adaptive thinking — el modelo decide cuánto razonar.
- Prompt caching sobre el system prompt (es estable; las tendencias van en el user turn).
- Streaming con `.get_final_message()` para evitar timeouts si max_tokens crece.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

try:
    import anthropic  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Falta anthropic. Ejecuta: pip install -r bot/requirements.txt") from exc

from config import NICHE, REGION_LABELS, Settings

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_user_message(
    settings: Settings,
    trends_md: str,
    youtube_md: str,
    tiktok_md: str,
) -> str:
    regions_human = ", ".join(f"{r} ({REGION_LABELS.get(r, '?')})" for r in settings.regions)
    today = date.today().isoformat()
    return f"""Genera el informe semanal de contenido para el nicho:

**{NICHE}**

Fecha de ejecución: {today}
Regiones objetivo: {regions_human}
Ventana temporal Google Trends: `{settings.timeframe}`

<trend_data>

## Google Trends
{trends_md}

## YouTube — videos PRL recientes
{youtube_md}

## TikTok Creative Center — hashtags trending generales
{tiktok_md}

</trend_data>

Sigue exactamente el formato de salida definido en tu rol. Si una fuente vino vacía, decláralo en la sección 4 sin inventar."""


def analyze(
    settings: Settings,
    trends_md: str,
    youtube_md: str,
    tiktok_md: str,
    effort: str = "high",
) -> str:
    """Devuelve el informe markdown generado por Claude."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system_prompt = _load_system_prompt()

    user_msg = build_user_message(settings, trends_md, youtube_md, tiktok_md)

    with client.messages.stream(
        model=settings.model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        final = stream.get_final_message()

    print()  # newline final
    _log_usage(final)
    return _extract_text(final)


def _extract_text(message) -> str:
    parts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip()


def _log_usage(message) -> None:
    u = message.usage
    cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
    print(
        f"\n--- usage: input={u.input_tokens} | "
        f"cache_write={cache_write} | cache_read={cache_read} | "
        f"output={u.output_tokens} | stop={message.stop_reason}"
    )
