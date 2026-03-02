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

_EMPTY_FEED = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<feed xmlns=\"http://www.w3.org/2005/Atom\" xmlns:arxiv=\"http://arxiv.org/schemas/atom\"></feed>
"""

_BIBTEX = """@misc{smith2025impact,
  title={Impact of Tests},
  author={Alice Smith and Bob Jones},
  year={2025}
}"""


def _build_client() -> HttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/query":
            if request.url.params.get("id_list") == "0000.00000":
                return httpx.Response(200, text=_EMPTY_FEED)
            return httpx.Response(200, text=_ARXIV_FEED)
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
