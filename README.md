# paper-finder

Production-quality Python CLI for finding papers from **arXiv** and **Semantic Scholar**.

## Features

- Search arXiv
- Search Semantic Scholar (requires `SEMANTIC_SCHOLAR_API_KEY`)
- Fetch one paper as JSON via `get`:
  - arXiv id (for example `2501.01234`)
  - DOI (for Semantic Scholar)
- Export BibTeX via `export`:
  - arXiv: official arXiv BibTeX endpoint
  - Semantic Scholar: provider BibTeX when available, fallback generated BibTeX

## Install (dev)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

## Configuration

Semantic Scholar access key:

```bash
export SEMANTIC_SCHOLAR_API_KEY=your_key_here
```

Optional HTTP tuning:

```bash
export PAPER_FINDER_HTTP_TIMEOUT=20
export PAPER_FINDER_HTTP_MAX_RETRIES=3
export PAPER_FINDER_HTTP_BACKOFF=0.5
```

## Usage

### Search

```bash
paper-finder search "agent orchestration" -s arxiv -n 5
paper-finder search "agent orchestration" -s semantic_scholar -n 5
paper-finder search "agent orchestration" -s all -n 5
paper-finder search "openclaw" -s arxiv -n 3 --jsonl
```

### Get (JSON)

```bash
paper-finder get 2501.01234
paper-finder get 10.1038/nature12373
paper-finder get 10.1038/nature12373 --source semantic_scholar
```

### Export (BibTeX)

```bash
paper-finder export 2501.01234
paper-finder export 10.1038/nature12373
paper-finder export 2501.01234 --source arxiv
```

## Development checks

```bash
ruff format --check .
ruff check .
mypy paper_finder
pytest
```

## License

MIT (see [LICENSE](LICENSE)).
