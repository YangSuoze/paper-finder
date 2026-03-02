import httpx
import pytest
from paper_finder.errors import NotFoundError
from paper_finder.http import HttpClient, RetryConfig
from paper_finder.providers import arxiv

_ARXIV_FEED = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<feed xmlns=\"http://www.w3.org/2005/Atom\" xmlns:arxiv=\"http://arxiv.org/schemas/atom\">
  <entry>
    <id>http://arxiv.org/abs/2501.01234v1</id>
    <published>2025-01-03T00:00:00Z</published>
    <title>  Impact   of   Tests </title>
    <summary>  First line\n second line  </summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <link rel=\"alternate\" href=\"http://arxiv.org/abs/2501.01234v1\" />
    <link title=\"pdf\" href=\"http://arxiv.org/pdf/2501.01234v1\" />
    <arxiv:doi>10.1000/example</arxiv:doi>
  </entry>
</feed>
"""

_ARXIV_FILTER_FEED = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<feed xmlns=\"http://www.w3.org/2005/Atom\" xmlns:arxiv=\"http://arxiv.org/schemas/atom\">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <published>2024-01-03T00:00:00Z</published>
    <title>Recent One</title>
    <summary>Recent paper one</summary>
    <author><name>Alice</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00002v1</id>
    <published>2023-01-03T00:00:00Z</published>
    <title>Older One</title>
    <summary>Old paper</summary>
    <author><name>Bob</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2501.00003v1</id>
    <published>2025-01-03T00:00:00Z</published>
    <title>Recent Two</title>
    <summary>Recent paper two</summary>
    <author><name>Carol</name></author>
  </entry>
</feed>
"""

_EMPTY_FEED = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<feed xmlns=\"http://www.w3.org/2005/Atom\" xmlns:arxiv=\"http://arxiv.org/schemas/atom\"></feed>
"""

_BIBTEX = """@misc{smith2025impact,
  title={Impact of Tests},
  author={Alice Smith and Bob Jones},
  year={2025}
}"""


def _build_client(
    *,
    search_feed: str = _ARXIV_FEED,
    search_max_results: list[int] | None = None,
) -> HttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/query":
            id_list = request.url.params.get("id_list")
            if id_list == "0000.00000":
                return httpx.Response(200, text=_EMPTY_FEED)
            if id_list:
                return httpx.Response(200, text=_ARXIV_FEED)
            if search_max_results is not None:
                max_results = request.url.params.get("max_results")
                search_max_results.append(int(max_results) if max_results is not None else -1)
            return httpx.Response(200, text=search_feed)
        if request.url.path == "/bibtex/2501.01234":
            return httpx.Response(200, text=_BIBTEX)
        return httpx.Response(404, text="not found")

    return HttpClient(
        retry=RetryConfig(max_retries=0),
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )


def test_arxiv_search_parses_papers() -> None:
    with _build_client() as client:
        papers = arxiv.search("impact tests", limit=1, client=client)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.source == "arxiv"
    assert paper.id == "2501.01234v1"
    assert paper.title == "Impact of Tests"
    assert paper.abstract == "First line second line"
    assert paper.year == 2025
    assert paper.doi == "10.1000/example"
    assert paper.pdf_url == "http://arxiv.org/pdf/2501.01234v1"
    assert [author.name for author in paper.authors] == ["Alice Smith", "Bob Jones"]


def test_arxiv_get_not_found() -> None:
    with _build_client() as client, pytest.raises(NotFoundError):
        arxiv.get("0000.00000", client=client)


def test_arxiv_export_bibtex() -> None:
    with _build_client() as client:
        bibtex = arxiv.export_bibtex("2501.01234", client=client)

    assert bibtex.startswith("@misc")
    assert "Impact of Tests" in bibtex


def test_arxiv_search_filters_by_year_and_overfetches() -> None:
    max_results_calls: list[int] = []
    with _build_client(
        search_feed=_ARXIV_FILTER_FEED, search_max_results=max_results_calls
    ) as client:
        papers = arxiv.search("impact tests", limit=2, client=client, since_year=2024)

    assert max_results_calls == [10]
    assert [paper.id for paper in papers] == ["2401.00001v1", "2501.00003v1"]


def test_arxiv_search_overfetch_caps_at_200() -> None:
    max_results_calls: list[int] = []
    with _build_client(
        search_feed=_ARXIV_FILTER_FEED, search_max_results=max_results_calls
    ) as client:
        _ = arxiv.search("impact tests", limit=50, client=client, since_year=2020)

    assert max_results_calls == [200]
