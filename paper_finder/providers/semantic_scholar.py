from __future__ import annotations

import httpx

from ..models import Author, Paper

S2_API = "https://api.semanticscholar.org/graph/v1"


def search(query: str, limit: int = 10, *, api_key: str | None, timeout: float = 20.0) -> list[Paper]:
    headers = {"User-Agent": "paper-finder/0.1"}
    if api_key:
        headers["x-api-key"] = api_key

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,url,year,authors,externalIds",
    }

    with httpx.Client(timeout=timeout, headers=headers) as client:
        r = client.get(f"{S2_API}/paper/search", params=params)
        r.raise_for_status()
        data = r.json()

    out: list[Paper] = []
    for item in data.get("data", []) or []:
        authors = [Author(name=a.get("name", "")) for a in (item.get("authors") or []) if a.get("name")]
        external = item.get("externalIds") or {}
        out.append(
            Paper(
                source="semantic_scholar",
                id=item.get("paperId") or item.get("url") or item.get("title") or "",
                title=item.get("title") or "",
                abstract=item.get("abstract"),
                url=item.get("url"),
                year=item.get("year"),
                doi=external.get("DOI"),
                authors=authors,
            )
        )

    return out
