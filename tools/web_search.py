"""Web search tool backed by a self-hosted SearXNG instance."""

import httpx

SEARXNG_URL = "http://localhost:8080/search"
MAX_RESULTS = 4


def web_search(query: str) -> str:
    """
    Search the web for current information (news, facts, prices, weather, etc.)
    that you don't already know or that may have changed since your training.

    Args:
        query: The search query, e.g. "погода в Баку сегодня".

    Returns:
        str: A few top search results (title, snippet, url), or an error message
            if the search backend is unreachable.
    """
    try:
        response = httpx.get(
            SEARXNG_URL,
            params={"q": query, "format": "json"},
            timeout=10.0,
        )
        response.raise_for_status()
        results = response.json().get("results", [])[:MAX_RESULTS]
    except Exception as exc:
        return f"Error: web search is unavailable ({exc})."

    if not results:
        return "No search results found."

    lines = []
    for r in results:
        title = r.get("title", "").strip()
        snippet = r.get("content", "").strip()
        url = r.get("url", "").strip()
        lines.append(f"- {title}: {snippet} ({url})")
    return "\n".join(lines)


__all__ = ["web_search"]
