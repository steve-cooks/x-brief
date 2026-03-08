import json
from pathlib import Path

from click.testing import CliRunner

from x_brief.cli import main


def write_config(path: Path) -> None:
    path.write_text(json.dumps({"tracked_accounts": ["example_org"]}), encoding="utf-8")


def test_fetch_exits_non_zero_when_bearer_token_is_missing(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path)
    monkeypatch.delenv("X_BRIEF_BEARER_TOKEN", raising=False)

    result = CliRunner().invoke(main, ["fetch", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "X_BRIEF_BEARER_TOKEN environment variable not set" in result.output


def test_brief_exits_non_zero_when_bearer_token_is_missing(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path)
    monkeypatch.delenv("X_BRIEF_BEARER_TOKEN", raising=False)

    result = CliRunner().invoke(main, ["brief", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "X_BRIEF_BEARER_TOKEN environment variable not set" in result.output


def test_init_writes_recent_interests_with_neutral_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"

    result = CliRunner().invoke(main, ["init", "--output", str(config_path)])

    assert result.exit_code == 0

    payload = json.loads(config_path.read_text(encoding="utf-8"))

    assert "interests" not in payload
    assert payload["recent_interests"] == [
        "developer tools",
        "open source",
        "engineering blogs",
    ]
    assert "steipete" not in payload["tracked_accounts"]
