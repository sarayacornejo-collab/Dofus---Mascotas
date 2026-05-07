"""Google Trends via pytrends — sin API key, datos por país."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TrendRow:
    region: str
    keyword: str
    interest: int  # 0-100 promediado en el timeframe
    rising_queries: list[str]
    top_queries: list[str]


def fetch_trends(
    keywords: list[str],
    regions: list[str],
    timeframe: str = "now 7-d",
    sleep_between: float = 1.5,
) -> list[TrendRow]:
    """Consulta interés por keyword/región y queries asociadas.

    pytrends limita a 5 keywords por consulta. Devuelve lo que pudo recuperar;
    los errores 429 o de red se omiten silenciosamente para no romper el flujo.
    """
    try:
        from pytrends.request import TrendReq  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Falta pytrends. Ejecuta: pip install -r bot/requirements.txt"
        ) from exc

    rows: list[TrendRow] = []
    pytrend = TrendReq(hl="es-419", tz=300, retries=2, backoff_factor=0.5)

    chunks = [keywords[i : i + 5] for i in range(0, len(keywords), 5)]

    for region in regions:
        for chunk in chunks:
            try:
                pytrend.build_payload(chunk, timeframe=timeframe, geo=region)
                interest_df = pytrend.interest_over_time()
                related = pytrend.related_queries()
            except Exception as exc:  # pragma: no cover - red/cuota
                print(f"  [trends] error en {region}/{chunk[:1]}…: {exc}")
                time.sleep(sleep_between)
                continue

            for kw in chunk:
                interest = 0
                if interest_df is not None and not interest_df.empty and kw in interest_df.columns:
                    interest = int(interest_df[kw].mean())

                rising: list[str] = []
                top: list[str] = []
                kw_related = related.get(kw, {}) if related else {}
                if kw_related:
                    rising_df = kw_related.get("rising")
                    top_df = kw_related.get("top")
                    if rising_df is not None and not rising_df.empty:
                        rising = rising_df["query"].head(5).tolist()
                    if top_df is not None and not top_df.empty:
                        top = top_df["query"].head(5).tolist()

                if interest or rising or top:
                    rows.append(
                        TrendRow(
                            region=region,
                            keyword=kw,
                            interest=interest,
                            rising_queries=rising,
                            top_queries=top,
                        )
                    )

            time.sleep(sleep_between)

    return rows


def to_markdown(rows: list[TrendRow]) -> str:
    if not rows:
        return "_(Sin datos de Google Trends recuperados.)_"
    by_region: dict[str, list[TrendRow]] = {}
    for r in rows:
        by_region.setdefault(r.region, []).append(r)

    out: list[str] = []
    for region, items in by_region.items():
        items.sort(key=lambda r: r.interest, reverse=True)
        out.append(f"### {region}")
        for it in items[:10]:
            out.append(
                f"- **{it.keyword}** (interés: {it.interest}/100) "
                f"| rising: {', '.join(it.rising_queries) or '—'} "
                f"| top: {', '.join(it.top_queries) or '—'}"
            )
        out.append("")
    return "\n".join(out)
