from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from ..errors import ConfigurationError, InputError, NotFoundError, ProviderError
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


def _escape_bibtex_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _sanitize_bibtex_key(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9]+", "", value.lower())
    return sanitized or "paper"


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

    pdf_url: str | None = None
    open_access_pdf = item.get("openAccessPdf")
    if isinstance(open_access_pdf, dict):
        pdf_url = _as_string(open_access_pdf.get("url"))

    paper_id = _as_string(item.get("paperId")) or _as_string(item.get("url")) or ""
    return Paper(
        source="semantic_scholar",
        id=paper_id,
        title=_as_string(item.get("title")) or "",
        abstract=_as_string(item.get("abstract")),
        url=_as_string(item.get("url")),
        pdf_url=pdf_url,
        year=_as_int(item.get("year")),
        doi=doi,
        authors=authors,
    )


def _build_fallback_bibtex(paper: Paper, doi: str) -> str:
    author_names = " and ".join(author.name for author in paper.authors) or "Unknown"
    year = str(paper.year) if paper.year is not None else "unknown"
    first_author = paper.authors[0].name.split()[-1] if paper.authors else "unknown"
    key = _sanitize_bibtex_key(f"{first_author}{year}")
    title = paper.title or f"Paper for DOI {doi}"

    entries = [
        f"  author = {{{_escape_bibtex_value(author_names)}}}",
        f"  title = {{{_escape_bibtex_value(title)}}}",
        f"  year = {{{_escape_bibtex_value(year)}}}",
        f"  doi = {{{_escape_bibtex_value(doi)}}}",
    ]
    if paper.url:
        entries.append(f"  url = {{{_escape_bibtex_value(paper.url)}}}")

    body = ",\n".join(entries)
    return f"@article{{{key},\n{body}\n}}"


def _validate_year_range(since_year: int | None, until_year: int | None) -> None:
    if since_year is not None and since_year < 1:
        raise InputError("--since-year must be greater than 0.")
    if until_year is not None and until_year < 1:
        raise InputError("--until-year must be greater than 0.")
    if since_year is not None and until_year is not None and since_year > until_year:
        raise InputError("--since-year cannot be greater than --until-year.")


def _build_year_range_param(since_year: int | None, until_year: int | None) -> str | None:
    if since_year is not None and until_year is not None:
        return f"{since_year}-{until_year}"
    if since_year is not None:
        return f"{since_year}-"
    if until_year is not None:
        return f"-{until_year}"
    return None


def _matches_year_range(
    paper: Paper, *, since_year: int | None = None, until_year: int | None = None
) -> bool:
    if since_year is None and until_year is None:
        return True
    if paper.year is None:
        return False
    if since_year is not None and paper.year < since_year:
        return False
    return not (until_year is not None and paper.year > until_year)


def search(
    query: str,
    *,
    limit: int,
    api_key: str | None,
    client: HttpClient,
    since_year: int | None = None,
    until_year: int | None = None,
) -> list[Paper]:
    if limit <= 0:
        raise InputError("--limit must be greater than 0.")
    _validate_year_range(since_year, until_year)

    key = _require_api_key(api_key)
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,url,openAccessPdf,year,authors,externalIds",
    }
    year_range_param = _build_year_range_param(since_year, until_year)
    if year_range_param is not None:
        params["year"] = year_range_param

    try:
        payload = client.get_json(
            f"{_BASE_URL}/paper/search",
            provider=_PROVIDER,
            params=params,
            headers=_headers(key),
        )
    except ProviderError as exc:
        # Fallback if upstream does not support the year query parameter.
        if year_range_param is None or exc.status_code not in {400, 422}:
            raise
        fallback_params = params.copy()
        fallback_params.pop("year", None)
        payload = client.get_json(
            f"{_BASE_URL}/paper/search",
            provider=_PROVIDER,
            params=fallback_params,
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
    filtered = [
        paper
        for paper in papers
        if _matches_year_range(paper, since_year=since_year, until_year=until_year)
    ]
    return filtered[:limit]


def get_by_doi(doi: str, *, api_key: str | None, client: HttpClient) -> Paper:
    normalized_doi = normalize_doi(doi)
    key = _require_api_key(api_key)
    encoded_doi = quote(normalized_doi, safe="")
    try:
        payload = client.get_json(
            f"{_BASE_URL}/paper/DOI:{encoded_doi}",
            provider=_PROVIDER,
            params={"fields": "title,abstract,url,openAccessPdf,year,authors,externalIds"},
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
