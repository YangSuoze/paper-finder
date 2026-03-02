from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..errors import InputError, NotFoundError, ProviderError
from ..http import HttpClient
from ..identifiers import normalize_arxiv_id
from ..models import Author, Paper

_PROVIDER = "arXiv"
_API_URL = "https://export.arxiv.org/api/query"
_BIBTEX_URL = "https://arxiv.org/bibtex"
_NAMESPACE = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _collapse_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = re.sub(r"\s+", " ", value).strip()
    return collapsed or None


def _extract_year(value: str | None) -> int | None:
    if not value or len(value) < 4:
        return None
    prefix = value[:4]
    return int(prefix) if prefix.isdigit() else None


def _extract_arxiv_id_from_entry_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"arxiv\.org/abs/(.+)$", url)
    if not match:
        return None
    candidate = match.group(1)
    try:
        return normalize_arxiv_id(candidate)
    except InputError:
        return candidate


def _parse_entry(entry: ET.Element) -> Paper:
    entry_url = _collapse_whitespace(entry.findtext("a:id", default="", namespaces=_NAMESPACE))
    title = _collapse_whitespace(entry.findtext("a:title", default="", namespaces=_NAMESPACE)) or ""
    abstract = _collapse_whitespace(entry.findtext("a:summary", default="", namespaces=_NAMESPACE))
    published = _collapse_whitespace(
        entry.findtext("a:published", default="", namespaces=_NAMESPACE)
    )
    doi = _collapse_whitespace(entry.findtext("arxiv:doi", default="", namespaces=_NAMESPACE))

    authors: list[Author] = []
    for author_node in entry.findall("a:author", _NAMESPACE):
        name = _collapse_whitespace(
            author_node.findtext("a:name", default="", namespaces=_NAMESPACE)
        )
        if name:
            authors.append(Author(name=name))

    pdf_url: str | None = None
    for link in entry.findall("a:link", _NAMESPACE):
        if link.attrib.get("title") == "pdf":
            pdf_url = link.attrib.get("href")
            break

    arxiv_id = _extract_arxiv_id_from_entry_url(entry_url)
    return Paper(
        source="arxiv",
        id=arxiv_id or entry_url or title,
        title=title,
        abstract=abstract,
        url=entry_url,
        pdf_url=pdf_url,
        doi=doi,
        year=_extract_year(published),
        authors=authors,
    )


def _parse_feed(xml_payload: str) -> list[Paper]:
    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError as exc:
        raise ProviderError(_PROVIDER, "arXiv returned malformed XML.") from exc

    papers: list[Paper] = []
    for entry in root.findall("a:entry", _NAMESPACE):
        papers.append(_parse_entry(entry))
    return papers


def search(query: str, *, limit: int, client: HttpClient) -> list[Paper]:
    if limit <= 0:
        raise InputError("--limit must be greater than 0.")

    params = {"search_query": f"all:{query}", "start": 0, "max_results": limit}
    payload = client.get_text(_API_URL, provider=_PROVIDER, params=params)
    papers = _parse_feed(payload)
    return papers[:limit]


def get(arxiv_id: str, *, client: HttpClient) -> Paper:
    normalized_id = normalize_arxiv_id(arxiv_id)
    params = {"id_list": normalized_id, "max_results": 1}
    payload = client.get_text(_API_URL, provider=_PROVIDER, params=params)
    papers = _parse_feed(payload)
    if not papers:
        raise NotFoundError(_PROVIDER, f'No arXiv paper found for id "{normalized_id}".')
    return papers[0]


def export_bibtex(arxiv_id: str, *, client: HttpClient) -> str:
    normalized_id = normalize_arxiv_id(arxiv_id)
    payload = client.get_text(f"{_BIBTEX_URL}/{normalized_id}", provider=_PROVIDER).strip()
    if not payload.startswith("@"):
        raise ProviderError(
            _PROVIDER, f"arXiv returned an unexpected BibTeX payload for {normalized_id}."
        )
    return payload
