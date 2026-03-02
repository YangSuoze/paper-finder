import pytest
from paper_finder.errors import InputError
from paper_finder.identifiers import (
    IdentifierKind,
    detect_identifier_kind,
    normalize_arxiv_id,
    normalize_doi,
)


def test_normalize_arxiv_id_accepts_prefixed_value() -> None:
    assert normalize_arxiv_id("arXiv:2501.01234v2") == "2501.01234v2"


def test_normalize_arxiv_id_rejects_invalid_value() -> None:
    with pytest.raises(InputError):
        normalize_arxiv_id("not-an-arxiv-id")


def test_normalize_doi_accepts_url_form() -> None:
    assert normalize_doi("https://doi.org/10.1038/nature12373") == "10.1038/nature12373"


def test_detect_identifier_kind_for_arxiv_and_doi() -> None:
    assert detect_identifier_kind("2501.01234") == IdentifierKind.ARXIV
    assert detect_identifier_kind("10.1038/nature12373") == IdentifierKind.DOI
