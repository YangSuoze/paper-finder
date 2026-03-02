from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import load_settings
from .providers import arxiv, semantic_scholar

app = typer.Typer(add_completion=False, help="Paper finder: arXiv + Semantic Scholar")
console = Console()


def _render(papers):
    table = Table(show_lines=False)
    table.add_column("#", justify="right")
    table.add_column("source")
    table.add_column("title")
    table.add_column("year", justify="right")
    table.add_column("url")
    for i, p in enumerate(papers, 1):
        table.add_row(str(i), p.source, p.title[:80], str(p.year or ""), p.url or "")
    console.print(table)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (English recommended)."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=50),
    source: str = typer.Option("arxiv", "--source", "-s", help="arxiv|semantic_scholar|all"),
    jsonl: bool = typer.Option(False, "--jsonl", help="Output JSONL to stdout."),
):
    """Search papers."""
    settings = load_settings()
    papers = []

    if source in ("arxiv", "all"):
        papers.extend(arxiv.search(query, limit=limit))

    if source in ("semantic_scholar", "all"):
        papers.extend(semantic_scholar.search(query, limit=limit, api_key=settings.semantic_scholar_api_key))

    if jsonl:
        for p in papers:
            print(json.dumps(p.model_dump(), ensure_ascii=False))
        return

    _render(papers)


def main():
    app()


if __name__ == "__main__":
    main()
