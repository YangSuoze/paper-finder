from paper_finder.providers import arxiv


def test_arxiv_search_smoke():
    papers = arxiv.search("openclaw", limit=1)
    assert len(papers) <= 1
    if papers:
        assert papers[0].title
