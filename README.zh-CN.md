# paper-finder（论文检索工具）

一个偏“工程化”的 Python 命令行工具，用于从 **arXiv** 与 **Semantic Scholar** 检索论文，并支持按年份过滤、获取详情（JSON）与导出 BibTeX。

> Python 版本：>= 3.11

## 功能

- 搜索 arXiv
- 搜索 Semantic Scholar（需要环境变量 `SEMANTIC_SCHOLAR_API_KEY`）
- 按年份过滤搜索结果：`--since-year` / `--until-year`（包含边界）
- 获取单篇论文 JSON：`paper-finder get <arxiv_id|doi>`
- 导出 BibTeX：`paper-finder export <arxiv_id|doi>`

## 安装（开发方式）

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

## 使用示例

### 1）搜索（arXiv）

```bash
paper-finder search "brain computer interface" -s arxiv -n 10
```

按年份过滤（例如 2025 年及以后）：

```bash
paper-finder search "brain computer interface" -s arxiv -n 20 --since-year 2025
```

### 2）搜索（Semantic Scholar）

先配置 API Key：

```bash
export SEMANTIC_SCHOLAR_API_KEY=你的key
```

再搜索：

```bash
paper-finder search "brain computer interface" -s semantic_scholar -n 10
paper-finder search "brain computer interface" -s semantic_scholar -n 10 --since-year 2023 --until-year 2025
```

### 3）获取单篇论文（JSON）

arXiv：

```bash
paper-finder get 2501.05589
```

DOI（Semantic Scholar）：

```bash
paper-finder get 10.1038/nature12373
```

### 4）导出 BibTeX

arXiv：

```bash
paper-finder export 2501.05589
```

DOI（Semantic Scholar）：

```bash
paper-finder export 10.1038/nature12373
```

## 输出格式

- 默认：人类可读的列表输出（title + year + url）
- `--jsonl`：每行一条 JSON（便于管道处理）
- `--json`：输出 JSON 数组（便于整体保存）

## 备注

- arXiv 使用官方 Atom API：<https://export.arxiv.org/api_help/docs/user-manual.html>
- Semantic Scholar Graph API：<https://api.semanticscholar.org/>
