# paper-finder

A clean, production-style CLI to search papers from **arXiv** and **Semantic Scholar**.

## Install (dev)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

## Usage

### arXiv
```bash
paper-finder search "openclaw codex agent" -s arxiv -n 5
```

### Semantic Scholar
Set API key as env var (optional but recommended):

```bash
export SEMANTIC_SCHOLAR_API_KEY=... 
paper-finder search "openclaw codex agent" -s semantic_scholar -n 5
```

### All sources
```bash
paper-finder search "agent orchestration" -s all -n 10
```

### JSONL output
```bash
paper-finder search "openclaw" -s arxiv -n 5 --jsonl
```

## Notes
- arXiv uses the official Atom API: https://export.arxiv.org/api_help/docs/user-manual.html
- Semantic Scholar Graph API: https://api.semanticscholar.org/
