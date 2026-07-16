import logging
from urllib.parse import quote

import httpx
from sqlmodel import Session

from app.models import Movie, Show
from app.settings_store import metadata_enabled

logger = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_REST = "https://en.wikipedia.org/api/rest_v1/page/summary"
USER_AGENT = "VLCouch/1.0 (personal local media app)"


def _search_page_title(query: str) -> str | None:
    try:
        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(
                WIKI_API,
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": 1,
                    "namespace": 0,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            titles = resp.json()[1]
            return titles[0] if titles else None
    except Exception as e:
        logger.debug("Wikipedia search failed for %r: %s", query, e)
        return None


def _fetch_overview(page_title: str) -> str | None:
    safe_title = quote(page_title.replace(" ", "_"), safe="()")
    url = f"{WIKI_REST}/{safe_title}"
    try:
        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            return data.get("extract") or data.get("description")
    except Exception as e:
        logger.debug("Wikipedia summary failed for %r: %s", page_title, e)
        return None


def lookup_overview(title: str, kind: str, year: int | None = None) -> str | None:
    """Look up a plot summary from Wikipedia. Text only — no images downloaded."""
    if not metadata_enabled():
        return None

    if kind == "movie":
        queries = []
        if year:
            queries.append(f"{title} ({year} film)")
        queries.append(f"{title} (film)")
        queries.append(title)
    else:
        queries = [f"{title} (TV series)", title]

    for query in queries:
        page_title = _search_page_title(query)
        if page_title:
            overview = _fetch_overview(page_title)
            if overview:
                return overview
    return None


def enrich_movie(session: Session, movie: Movie) -> None:
    if movie.overview:
        return
    overview = lookup_overview(movie.title, "movie", movie.year)
    if overview:
        movie.overview = overview
        session.add(movie)
        session.commit()


def enrich_show(session: Session, show: Show) -> None:
    if show.overview:
        return
    try:
        overview = lookup_overview(show.title, "tv")
        if overview:
            show.overview = overview
            session.add(show)
            session.commit()
    except Exception as e:
        # Log the error but don't fail the entire request
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Error enriching show %d (%s): %s", show.id, show.title, str(e))
