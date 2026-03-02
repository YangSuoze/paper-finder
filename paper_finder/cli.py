from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated

import typer

from .config import Settings, load_settings
from .errors import ConfigurationError, InputError, PaperFinderError
from .http import HttpClient, RetryConfig
from .identifiers import IdentifierKind, detect_identifier_kind, normalize_arxiv_id, normalize_doi
from .models import Paper
from .providers import arxiv, semantic_scholar

app = typer.Typer(
    add_completion=False,
    help="Paper finder CLI for arXiv and Semantic Scholar.",
    no_args_is_help=True,
)


class SearchSource(StrEnum):
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    ALL = "all"


class GetSource(StrEnum):
    AUTO = "auto"
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"


def _error_and_exit(message: str) -> None:
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def _print_papers_table(papers: list[Paper]) -> None:
    if not papers:
        typer.echo("No papers found.")
        return

    for index, paper in enumerate(papers, start=1):
        year = str(paper.year) if paper.year is not None else "n/a"
        typer.echo(f"{index:>2}. [{paper.source}] {paper.title} ({year})")
        if paper.url:
            typer.echo(f"    {paper.url}")


def _print_json(payload: dict[str, object]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def _build_http_client(settings: Settings) -> HttpClient:
    retry = RetryConfig(
        max_retries=settings.http_max_retries,
        backoff_seconds=settings.http_backoff_seconds,
    )
    return HttpClient(timeout_seconds=settings.http_timeout_seconds, retry=retry)


def _require_semantic_api_key(settings: Settings) -> str:
    key = settings.semantic_scholar_api_key
    if not key:
        raise ConfigurationError(
            "SEMANTIC_SCHOLAR_API_KEY is required for Semantic Scholar commands."
        )
    return key


def _resolve_get_source(identifier: str, source: GetSource) -> GetSource:
    if source != GetSource.AUTO:
        return source

    detected = detect_identifier_kind(identifier)
    if detected == IdentifierKind.ARXIV:
        return GetSource.ARXIV
    return GetSource.SEMANTIC_SCHOLAR


def _search_papers(query: str, limit: int, source: SearchSource, settings: Settings) -> list[Paper]:
    papers: list[Paper] = []
    with _build_http_client(settings) as client:
        if source in {SearchSource.ARXIV, SearchSource.ALL}:
            papers.extend(arxiv.search(query, limit=limit, client=client))
        if source in {SearchSource.SEMANTIC_SCHOLAR, SearchSource.ALL}:
            key = _require_semantic_api_key(settings)
            papers.extend(semantic_scholar.search(query, limit=limit, api_key=key, client=client))
    return papers


def _get_paper(identifier: str, source: GetSource, settings: Settings) -> Paper:
    resolved_source = _resolve_get_source(identifier, source)
    with _build_http_client(settings) as client:
        if resolved_source == GetSource.ARXIV:
            return arxiv.get(normalize_arxiv_id(identifier), client=client)
        key = _require_semantic_api_key(settings)
        return semantic_scholar.get_by_doi(normalize_doi(identifier), api_key=key, client=client)


def _export_bibtex(identifier: str, source: GetSource, settings: Settings) -> str:
    resolved_source = _resolve_get_source(identifier, source)
    with _build_http_client(settings) as client:
        if resolved_source == GetSource.ARXIV:
            return arxiv.export_bibtex(normalize_arxiv_id(identifier), client=client)
        key = _require_semantic_api_key(settings)
        return semantic_scholar.export_bibtex_by_doi(
            normalize_doi(identifier), api_key=key, client=client
        )


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query.")],
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", min=1, max=50, help="Results per source."),
    ] = 10,
    source: Annotated[
        SearchSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Source: arxiv, semantic_scholar, or all.",
        ),
    ] = SearchSource.ARXIV,
    jsonl: Annotated[
        bool,
        typer.Option("--jsonl", help="Output one JSON document per line."),
    ] = False,
) -> None:
    """Search papers by query."""
    try:
        papers = _search_papers(query=query, limit=limit, source=source, settings=load_settings())
    except PaperFinderError as exc:
        _error_and_exit(str(exc))

    if jsonl:
        for paper in papers:
            typer.echo(json.dumps(paper.model_dump(exclude_none=True), ensure_ascii=False))
        return

    _print_papers_table(papers)


@app.command()
def get(
    identifier: Annotated[str, typer.Argument(help="arXiv id (e.g. 2501.01234) or DOI.")],
    source: Annotated[
        GetSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Source: auto, arxiv, semantic_scholar.",
        ),
    ] = GetSource.AUTO,
) -> None:
    """Fetch a single paper by arXiv id or DOI and print JSON."""
    try:
        paper = _get_paper(identifier=identifier, source=source, settings=load_settings())
    except PaperFinderError as exc:
        _error_and_exit(str(exc))

    _print_json(paper.model_dump(exclude_none=True))


@app.command()
def export(
    identifier: Annotated[str, typer.Argument(help="arXiv id (e.g. 2501.01234) or DOI.")],
    source: Annotated[
        GetSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Source: auto, arxiv, semantic_scholar.",
        ),
    ] = GetSource.AUTO,
) -> None:
    """Export a paper citation as BibTeX."""
    try:
        bibtex = _export_bibtex(identifier=identifier, source=source, settings=load_settings())
    except PaperFinderError as exc:
        _error_and_exit(str(exc))

    typer.echo(bibtex)


def main() -> None:
    try:
        app()
    except InputError as exc:
        _error_and_exit(str(exc))


if __name__ == "__main__":
    main()
