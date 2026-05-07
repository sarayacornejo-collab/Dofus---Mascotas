"""YouTube Data API v3 — videos populares por keyword/región (últimos 7 días)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class YTVideo:
    region: str
    keyword: str
    title: str
    channel: str
    views: int
    likes: int
    published_at: str
    url: str


def fetch_youtube(
    api_key: str,
    keywords: list[str],
    regions: list[str],
    days_back: int = 7,
    per_keyword: int = 5,
) -> list[YTVideo]:
    """Devuelve videos recientes ordenados por viewCount para cada keyword/región."""
    if not api_key:
        return []

    try:
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.errors import HttpError  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Falta google-api-python-client. Ejecuta: pip install -r bot/requirements.txt"
        ) from exc

    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
    published_after = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    results: list[YTVideo] = []
    for region in regions:
        for kw in keywords:
            try:
                search = (
                    youtube.search()
                    .list(
                        q=kw,
                        part="id,snippet",
                        type="video",
                        regionCode=region,
                        relevanceLanguage="es",
                        publishedAfter=published_after,
                        order="viewCount",
                        maxResults=per_keyword,
                    )
                    .execute()
                )
            except HttpError as exc:  # pragma: no cover
                print(f"  [youtube] error {region}/{kw}: {exc}")
                continue

            video_ids = [
                item["id"]["videoId"]
                for item in search.get("items", [])
                if item.get("id", {}).get("videoId")
            ]
            if not video_ids:
                continue

            try:
                stats = (
                    youtube.videos()
                    .list(part="statistics,snippet", id=",".join(video_ids))
                    .execute()
                )
            except HttpError as exc:  # pragma: no cover
                print(f"  [youtube] stats error {region}/{kw}: {exc}")
                continue

            for it in stats.get("items", []):
                snip = it.get("snippet", {})
                st = it.get("statistics", {})
                results.append(
                    YTVideo(
                        region=region,
                        keyword=kw,
                        title=snip.get("title", ""),
                        channel=snip.get("channelTitle", ""),
                        views=int(st.get("viewCount", 0)),
                        likes=int(st.get("likeCount", 0)),
                        published_at=snip.get("publishedAt", ""),
                        url=f"https://youtube.com/watch?v={it['id']}",
                    )
                )

    return results


def to_markdown(videos: list[YTVideo]) -> str:
    if not videos:
        return "_(Sin datos de YouTube — define YOUTUBE_API_KEY o revisa cuota.)_"
    by_region: dict[str, list[YTVideo]] = {}
    for v in videos:
        by_region.setdefault(v.region, []).append(v)

    out: list[str] = []
    for region, items in by_region.items():
        items.sort(key=lambda v: v.views, reverse=True)
        out.append(f"### {region} — top videos PRL últimos días")
        for v in items[:10]:
            out.append(
                f"- [{v.title}]({v.url}) — *{v.channel}* "
                f"({v.views:,} views, {v.likes:,} likes) [{v.keyword}]"
            )
        out.append("")
    return "\n".join(out)
