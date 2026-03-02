from urllib.parse import unquote

import httpx
import pytest
from paper_finder.errors import ConfigurationError, InputError, NotFoundError
from paper_finder.http import HttpClient, RetryConfig
from paper_finder.providers import semantic_scholar

_API_KEY = "test-key"
_DEFAULT_SEARCH_DATA = [
    {
        "paperId": "abc123",
        "title": "Neural Testing",
        "abstract": "A paper about tests",
        "url": "https://example.org/paper/abc123",
        "openAccessPdf": {"url": "https://example.org/paper/abc123.pdf"},
        "year": 2024,
        "authors": [{"name": "Ada Lovelace"}],
        "externalIds": {"DOI": "10.1000/example"},
    }
]


def _build_client(
    *,
    include_bibtex: bool = True,
    not_found: bool = False,
    search_data: list[dict[str, object]] | None = None,
    capture_search_year: list[str | None] | None = None,
    reject_search_year_param: bool = False,
) -> HttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/paper/search"):
            year_param = request.url.params.get("year")
            if capture_search_year is not None:
                capture_search_year.append(year_param)
            if reject_search_year_param and year_param is not None:
                return httpx.Response(400, text="unsupported year parameter")
            return httpx.Response(
                200,
                json={"data": search_data if search_data is not None else _DEFAULT_SEARCH_DATA},
            )

        if "/paper/DOI:" in request.url.path:
            doi = unquote(request.url.path.split("DOI:", maxsplit=1)[1])
            if not_found or doi == "10.0000/missing":
                return httpx.Response(404, text="missing")

            payload = {
                "paperId": "abc123",
                "title": "Neural Testing",
                "url": "https://example.org/paper/abc123",
                "openAccessPdf": {"url": "https://example.org/paper/abc123.pdf"},
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
    assert paper.pdf_url == "https://example.org/paper/abc123.pdf"


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


def test_semantic_search_validates_limit() -> None:
    with _build_client() as client, pytest.raises(InputError):
        semantic_scholar.search("query", limit=0, api_key=_API_KEY, client=client)


def test_semantic_get_not_found() -> None:
    with _build_client(not_found=True) as client, pytest.raises(NotFoundError):
        semantic_scholar.get_by_doi("10.0000/missing", api_key=_API_KEY, client=client)


def test_semantic_search_uses_year_query_and_filters() -> None:
    year_params: list[str | None] = []
    with _build_client(
        capture_search_year=year_params,
        search_data=[
            {
                "paperId": "old",
                "title": "Old",
                "year": 2021,
                "authors": [{"name": "A"}],
                "externalIds": {"DOI": "10.1000/old"},
            },
            {
                "paperId": "new",
                "title": "New",
                "year": 2024,
                "authors": [{"name": "B"}],
                "externalIds": {"DOI": "10.1000/new"},
            },
        ],
    ) as client:
        papers = semantic_scholar.search(
            "neural testing",
            limit=5,
            api_key=_API_KEY,
            client=client,
            since_year=2023,
            until_year=2024,
        )

    assert year_params == ["2023-2024"]
    assert [paper.id for paper in papers] == ["new"]


def test_semantic_search_falls_back_when_year_param_unsupported() -> None:
    year_params: list[str | None] = []
    with _build_client(
        capture_search_year=year_params,
        reject_search_year_param=True,
        search_data=[
            {
                "paperId": "old",
                "title": "Old",
                "year": 2022,
                "authors": [{"name": "A"}],
                "externalIds": {"DOI": "10.1000/old"},
            },
            {
                "paperId": "new",
                "title": "New",
                "year": 2024,
                "authors": [{"name": "B"}],
                "externalIds": {"DOI": "10.1000/new"},
            },
        ],
    ) as client:
        papers = semantic_scholar.search(
            "neural testing",
            limit=5,
            api_key=_API_KEY,
            client=client,
            since_year=2024,
        )

    assert year_params == ["2024-", None]
    assert [paper.id for paper in papers] == ["new"]
