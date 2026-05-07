"""CLI orquestador del bot de tendencias PRL/SST.

Uso:
    python bot/main.py                          # ejecuta con defaults del .env
    python bot/main.py --regions ES,MX --skip-tiktok
    python bot/main.py --output reports/2026-W19.md --effort medium
    python bot/main.py --dry-run                # solo recolecta, no llama Claude
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

# Permite ejecutar con `python bot/main.py` desde la raíz del repo
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from config import SEED_KEYWORDS, Settings
from sources import google_trends, tiktok_creative, youtube


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Bot de tendencias PRL/SST → propuestas Reels/TikTok"
    )
    p.add_argument("--regions", help="Lista CSV de códigos ISO país (ej: ES,MX,AR)")
    p.add_argument("--timeframe", help="Ventana Google Trends (ej: now 7-d, today 1-m)")
    p.add_argument("--keywords", help="Lista CSV de keywords semilla; si se omite usa el set por defecto")
    p.add_argument("--skip-trends", action="store_true", help="Salta Google Trends")
    p.add_argument("--skip-youtube", action="store_true", help="Salta YouTube")
    p.add_argument("--skip-tiktok", action="store_true", help="Salta TikTok Creative Center")
    p.add_argument(
        "--effort",
        default="high",
        choices=["low", "medium", "high", "max", "xhigh"],
        help="Effort del modelo (default: high)",
    )
    p.add_argument(
        "--output",
        help="Ruta de salida del informe markdown. Si se omite, solo imprime a stdout.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo recolecta tendencias e imprime el bloque trend_data; no llama a Claude.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    settings = Settings()
    if args.regions:
        settings.regions = [r.strip().upper() for r in args.regions.split(",") if r.strip()]
    if args.timeframe:
        settings.timeframe = args.timeframe

    keywords = SEED_KEYWORDS
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    problems = settings.validate()
    if problems and not args.dry_run:
        for p in problems:
            print(f"⚠️  {p}", file=sys.stderr)
        if any("ANTHROPIC_API_KEY" in p for p in problems):
            return 2

    print(f"▶ Regiones: {settings.regions}")
    print(f"▶ Keywords: {len(keywords)} semillas")
    print(f"▶ Timeframe Trends: {settings.timeframe}")
    print(f"▶ Modelo: {settings.model}")
    print()

    # 1. Google Trends
    if args.skip_trends:
        trends_md = "_(Saltado por --skip-trends.)_"
    else:
        print("⏳ Consultando Google Trends…")
        rows = google_trends.fetch_trends(keywords, settings.regions, settings.timeframe)
        trends_md = google_trends.to_markdown(rows)
        print(f"   → {len(rows)} filas recuperadas")

    # 2. YouTube
    if args.skip_youtube or not settings.youtube_api_key:
        if not settings.youtube_api_key and not args.skip_youtube:
            print("⏭  YouTube: YOUTUBE_API_KEY no definida, saltando.")
        youtube_md = "_(Saltado o sin API key.)_"
    else:
        print("⏳ Consultando YouTube Data API…")
        videos = youtube.fetch_youtube(settings.youtube_api_key, keywords, settings.regions)
        youtube_md = youtube.to_markdown(videos)
        print(f"   → {len(videos)} videos recuperados")

    # 3. TikTok Creative Center
    if args.skip_tiktok:
        tiktok_md = "_(Saltado por --skip-tiktok.)_"
    else:
        print("⏳ Consultando TikTok Creative Center…")
        hashtags = tiktok_creative.fetch_trending_hashtags(settings.regions)
        tiktok_md = tiktok_creative.to_markdown(hashtags)
        print(f"   → {len(hashtags)} hashtags recuperados")

    print()

    if args.dry_run:
        print("=" * 60)
        print("DRY RUN — bloque trend_data:")
        print("=" * 60)
        print("## Google Trends\n" + trends_md)
        print("\n## YouTube\n" + youtube_md)
        print("\n## TikTok\n" + tiktok_md)
        return 0

    print("⏳ Llamando a Claude para análisis…\n")
    print("=" * 60)
    from analyzer import analyze  # import diferido para que --dry-run funcione sin anthropic

    report = analyze(settings, trends_md, youtube_md, tiktok_md, effort=args.effort)
    print("=" * 60)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_wrap_report(report, settings), encoding="utf-8")
        print(f"\n✅ Informe guardado en {out_path}")

    return 0


def _wrap_report(report: str, settings: Settings) -> str:
    return (
        f"# Informe de tendencias PRL/SST — {date.today().isoformat()}\n\n"
        f"_Regiones: {', '.join(settings.regions)} · Modelo: {settings.model}_\n\n"
        f"---\n\n{report}\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
