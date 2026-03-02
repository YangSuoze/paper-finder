import json

from paper_finder import cli
from paper_finder.config import Settings
from paper_finder.models import Author, Paper
from typer.testing import CliRunner

runner = CliRunner()


def test_get_command_outputs_json(monkeypatch) -> None:
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(semantic_scholar_api_key="k"))
    monkeypatch.setattr(
        cli,
        "_get_paper",
        lambda identifier, source, settings: Paper(
            source="arxiv",
            id="2501.01234",
            title="Title",
            authors=[Author(name="Ada")],
        ),
    )

    result = runner.invoke(cli.app, ["get", "2501.01234"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["source"] == "arxiv"
    assert payload["id"] == "2501.01234"


def test_export_command_outputs_bibtex(monkeypatch) -> None:
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(semantic_scholar_api_key="k"))
    monkeypatch.setattr(cli, "_export_bibtex", lambda identifier, source, settings: "@article{key}")

    result = runner.invoke(cli.app, ["export", "10.1000/example"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "@article{key}"
