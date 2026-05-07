"""TikTok Creative Center — endpoint público de hashtags trending.

Es scraping best-effort sobre `ads.tiktok.com/business/creativecenter`. El
endpoint cambia con frecuencia: si falla, el bot continúa sin estos datos.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

# Mapeo aproximado país -> code que usa Creative Center
COUNTRY_MAP = {
    "ES": "ES",
    "MX": "MX",
    "AR": "AR",
    "CO": "CO",
    "CL": "CL",
    "PE": "PE",
    "EC": "EC",
    "UY": "UY",
    "DO": "DO",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9",
}


@dataclass
class TTHashtag:
    region: str
    hashtag: str
    rank: int
    publish_count: int
    video_views: int


def fetch_trending_hashtags(regions: list[str], period: int = 7, top_n: int = 30) -> list[TTHashtag]:
    """Pull de hashtags trending por país. period: 7|30|120 días."""
    out: list[TTHashtag] = []
    base = "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"

    for region in regions:
        cc = COUNTRY_MAP.get(region.upper())
        if not cc:
            continue
        params = {
            "page": 1,
            "limit": top_n,
            "period": period,
            "country_code": cc,
            "sort_by": "popular",
        }
        try:
            r = requests.get(base, params=params, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"  [tiktok] {region}: HTTP {r.status_code}")
                continue
            data = r.json()
        except (requests.RequestException, ValueError) as exc:  # pragma: no cover
            print(f"  [tiktok] {region}: {exc}")
            continue

        items = (data.get("data") or {}).get("list") or []
        for it in items:
            out.append(
                TTHashtag(
                    region=region,
                    hashtag=it.get("hashtag_name") or it.get("name") or "",
                    rank=int(it.get("rank") or 0),
                    publish_count=int(it.get("publish_cnt") or 0),
                    video_views=int(it.get("video_views") or 0),
                )
            )

    return out


def to_markdown(hashtags: list[TTHashtag]) -> str:
    if not hashtags:
        return (
            "_(Sin datos de TikTok Creative Center. El endpoint puede haber cambiado o "
            "estar geo-bloqueado; el resto del análisis sigue siendo válido.)_"
        )
    by_region: dict[str, list[TTHashtag]] = {}
    for h in hashtags:
        by_region.setdefault(h.region, []).append(h)

    out: list[str] = []
    for region, items in by_region.items():
        items.sort(key=lambda h: h.rank or 9999)
        out.append(f"### {region} — hashtags top (no PRL-específicos, contexto general)")
        for h in items[:15]:
            views = f"{h.video_views:,}" if h.video_views else "—"
            posts = f"{h.publish_count:,}" if h.publish_count else "—"
            out.append(f"- #{h.hashtag} (rank {h.rank}, {posts} posts, {views} views)")
        out.append("")
    return "\n".join(out)
