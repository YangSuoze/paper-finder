from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ..errors import ConfigurationError, NotFoundError, ProviderError
from ..http import HttpClient
from ..identifiers import normalize_doi
from ..models import Author, Paper

_PROVIDER = "Semantic Scholar"
_BASE_URL = "https://api.semanticscholar.org/graph/v1"


def _headers(api_key: str) -> dict[str, str]:
    return {"x-api-key": api_key}


def _require_api_key(api_key: str | None) -> str:
    if not api_key:
        raise ConfigurationError(
            "SEMANTIC_SCHOLAR_API_KEY is required for Semantic Scholar commands."
        )
    return api_key


def _as_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _map_paper(item: dict[str, Any]) -> Paper:
    authors_raw = item.get("authors")
    authors: list[Author] = []
    if isinstance(authors_raw, list):
        for author in authors_raw:
            if not isinstance(author, dict):
                continue
            name = _as_string(author.get("name"))
            if name:
                authors.append(Author(name=name))

    external_ids = item.get("externalIds")
    doi: str | None = None
    if isinstance(external_ids, dict):
        doi = _as_string(external_ids.get("DOI"))

    paper_id = _as_string(item.get("paperId")) or _as_string(item.get("url")) or ""
    return Paper(
        source="semantic_scholar",
        id=paper_id,
        title=_as_string(item.get("title")) or "",
        abstract=_as_string(item.get("abstract")),
        url=_as_string(item.get("url")),
        year=_as_int(item.get("year")),
        doi=doi,
        authors=authors,
    )


def _build_fallback_bibtex(paper: Paper, doi: str) -> str:
    author_names = " and ".join(author.name for author in paper.authors) or "Unknown"
    year = str(paper.year) if paper.year is not None else "unknown"
    first_author = paper.authors[0].name.split()[-1].lower() if paper.authors else "unknown"
    key = f"{first_author}{year}"
    title = paper.title or f"Paper for DOI {doi}"

    entries = [
        f"  author = {{{author_names}}}",
        f"  title = {{{title}}}",
        f"  year = {{{year}}}",
        f"  doi = {{{doi}}}",
    ]
    if paper.url:
        entries.append(f"  url = {{{paper.url}}}")

    body = ",\n".join(entries)
    return f"@article{{{key},\n{body}\n}}"


def search(query: str, *, limit: int, api_key: str | None, client: HttpClient) -> list[Paper]:
    key = _require_api_key(api_key)
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,url,year,authors,externalIds",
    }
    payload = client.get_json(
        f"{_BASE_URL}/paper/search",
        provider=_PROVIDER,
        params=params,
        headers=_headers(key),
    )

    data = payload.get("data")
    if not isinstance(data, list):
        raise ProviderError(
            _PROVIDER, "Semantic Scholar returned an unexpected search response shape."
        )

    papers: list[Paper] = []
    for item in data:
        if isinstance(item, dict):
            papers.append(_map_paper(item))
    return papers[:limit]


def get_by_doi(doi: str, *, api_key: str | None, client: HttpClient) -> Paper:
    normalized_doi = normalize_doi(doi)
    key = _require_api_key(api_key)
    encoded_doi = quote(normalized_doi, safe="")
    try:
        payload = client.get_json(
            f"{_BASE_URL}/paper/DOI:{encoded_doi}",
            provider=_PROVIDER,
            params={"fields": "title,abstract,url,year,authors,externalIds"},
            headers=_headers(key),
        )
    except NotFoundError as exc:
        raise NotFoundError(
            _PROVIDER, f'No Semantic Scholar paper found for DOI "{normalized_doi}".'
        ) from exc

    paper = _map_paper(payload)
    if not paper.doi:
        paper = paper.model_copy(update={"doi": normalized_doi})
    return paper


def export_bibtex_by_doi(doi: str, *, api_key: str | None, client: HttpClient) -> str:
    normalized_doi = normalize_doi(doi)
    key = _require_api_key(api_key)
    encoded_doi = quote(normalized_doi, safe="")
    try:
        payload = client.get_json(
            f"{_BASE_URL}/paper/DOI:{encoded_doi}",
            provider=_PROVIDER,
            params={"fields": "title,year,authors,url,externalIds,citationStyles"},
            headers=_headers(key),
        )
    except NotFoundError as exc:
        raise NotFoundError(
            _PROVIDER, f'No Semantic Scholar paper found for DOI "{normalized_doi}".'
        ) from exc

    citation_styles = payload.get("citationStyles")
    if isinstance(citation_styles, dict):
        bibtex = citation_styles.get("bibtex")
        if isinstance(bibtex, str) and bibtex.strip():
            return bibtex.strip()

    paper = _map_paper(payload)
    return _build_fallback_bibtex(paper, normalized_doi)
