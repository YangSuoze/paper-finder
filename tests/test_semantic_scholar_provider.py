from urllib.parse import unquote

import httpx
import pytest
from paper_finder.errors import ConfigurationError, NotFoundError
from paper_finder.http import HttpClient, RetryConfig
from paper_finder.providers import semantic_scholar

_API_KEY = "test-key"


def _build_client(*, include_bibtex: bool = True, not_found: bool = False) -> HttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/paper/search"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "paperId": "abc123",
                            "title": "Neural Testing",
                            "abstract": "A paper about tests",
                            "url": "https://example.org/paper/abc123",
                            "year": 2024,
                            "authors": [{"name": "Ada Lovelace"}],
                            "externalIds": {"DOI": "10.1000/example"},
                        }
                    ]
                },
            )

        if "/paper/DOI:" in request.url.path:
            doi = unquote(request.url.path.split("DOI:", maxsplit=1)[1])
            if not_found or doi == "10.0000/missing":
                return httpx.Response(404, text="missing")

            payload = {
                "paperId": "abc123",
                "title": "Neural Testing",
                "url": "https://example.org/paper/abc123",
                "year": 2024,
                "authors": [{"name": "Ada Lovelace"}],
                "externalIds": {"DOI": doi},
            }
            if include_bibtex:
                payload["citationStyles"] = {
                    "bibtex": "@article{lovelace2024neural,title={Neural Testing}}"
                }
            return httpx.Response(200, json=payload)

        return httpx.Response(404, text="not found")

    return HttpClient(
        retry=RetryConfig(max_retries=0),
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )


def test_semantic_search_parses_papers() -> None:
    with _build_client() as client:
        papers = semantic_scholar.search("neural testing", limit=5, api_key=_API_KEY, client=client)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.source == "semantic_scholar"
    assert paper.id == "abc123"
    assert paper.doi == "10.1000/example"


def test_semantic_get_by_doi() -> None:
    with _build_client() as client:
        paper = semantic_scholar.get_by_doi("10.1000/example", api_key=_API_KEY, client=client)

    assert paper.title == "Neural Testing"
    assert paper.doi == "10.1000/example"


def test_semantic_export_bibtex_from_citation_styles() -> None:
    with _build_client(include_bibtex=True) as client:
        bibtex = semantic_scholar.export_bibtex_by_doi(
            "10.1000/example", api_key=_API_KEY, client=client
        )

    assert bibtex.startswith("@article")
    assert "Neural Testing" in bibtex


def test_semantic_export_bibtex_fallback_builder() -> None:
    with _build_client(include_bibtex=False) as client:
        bibtex = semantic_scholar.export_bibtex_by_doi(
            "10.1000/example", api_key=_API_KEY, client=client
        )

    assert bibtex.startswith("@article")
    assert "doi = {10.1000/example}" in bibtex


def test_semantic_commands_require_api_key() -> None:
    with _build_client() as client, pytest.raises(ConfigurationError):
        semantic_scholar.search("query", limit=1, api_key=None, client=client)


def test_semantic_get_not_found() -> None:
    with _build_client(not_found=True) as client, pytest.raises(NotFoundError):
        semantic_scholar.get_by_doi("10.0000/missing", api_key=_API_KEY, client=client)
