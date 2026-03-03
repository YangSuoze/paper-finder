# paper-finder

A production-quality Python CLI for finding papers from **arXiv** and **Semantic Scholar**.

- **English / 中文**: This README is bilingual. Search for `ENGLISH` / `中文` headings.
- Python: **>= 3.11**

---

## ENGLISH

### Features

- Search arXiv
- Search Semantic Scholar (requires `SEMANTIC_SCHOLAR_API_KEY`)
- Filter search results by publication year with `--since-year` / `--until-year` (inclusive)
- Fetch one paper as JSON via `get`:
  - arXiv id (e.g. `2501.01234`)
  - DOI (for Semantic Scholar)
- Export BibTeX via `export`:
  - arXiv: official arXiv BibTeX endpoint
  - Semantic Scholar: provider BibTeX when available; fallback generated BibTeX

### Install (dev)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

### Configuration

Semantic Scholar API key:

```bash
export SEMANTIC_SCHOLAR_API_KEY=your_key_here
```

Optional HTTP tuning:

```bash
export PAPER_FINDER_HTTP_TIMEOUT=20
export PAPER_FINDER_HTTP_MAX_RETRIES=3
```

### Usage

Search:

```bash
paper-finder search "brain computer interface" -s arxiv -n 10
paper-finder search "brain computer interface" -s semantic_scholar -n 10
paper-finder search "brain computer interface" -s all -n 10
paper-finder search "llm evals" -s arxiv -n 20 --since-year 2025
paper-finder search "llm evals" -s semantic_scholar -n 20 --since-year 2023 --until-year 2026
```

JSON output:

```bash
paper-finder search "openclaw" -s arxiv -n 3 --jsonl
paper-finder search "openclaw" -s arxiv -n 3 --json
```

Get (JSON):

```bash
paper-finder get 2501.01234
paper-finder get 10.1038/nature12373
```

Export BibTeX:

```bash
paper-finder export 2501.01234
paper-finder export 10.1038/nature12373
```

---

## 中文

一个偏“工程化”的 Python 命令行工具，用于从 **arXiv** 与 **Semantic Scholar** 检索论文，并支持按年份过滤、获取详情（JSON）与导出 BibTeX。

### 功能

- 搜索 arXiv
- 搜索 Semantic Scholar（需要环境变量 `SEMANTIC_SCHOLAR_API_KEY`）
- 按年份过滤搜索结果：`--since-year` / `--until-year`（包含边界）
- 获取单篇论文 JSON：`paper-finder get <arxiv_id|doi>`
- 导出 BibTeX：`paper-finder export <arxiv_id|doi>`

### 安装（开发方式）

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

### 配置

Semantic Scholar API Key（可选但建议配置，未配置会无法使用 Semantic Scholar 搜索）：

```bash
export SEMANTIC_SCHOLAR_API_KEY=你的key
```

### 用法

```bash
paper-finder search "brain computer interface" -s arxiv -n 10
paper-finder search "brain computer interface" -s all -n 10
paper-finder search "brain computer interface" -s arxiv -n 20 --since-year 2025

paper-finder get 2501.01234
paper-finder export 2501.01234
```

---

## References

- arXiv API: <https://export.arxiv.org/api_help/docs/user-manual.html>
- Semantic Scholar Graph API: <https://api.semanticscholar.org/>
