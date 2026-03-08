import json
from pathlib import Path

from click.testing import CliRunner

import x_brief.cli as cli_module
from x_brief.cli import main


def write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "tracked_accounts": ["example_org"],
                "recent_interests": ["developer tools"],
            }
        ),
        encoding="utf-8",
    )


def test_fetch_command_is_removed(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path)

    result = CliRunner().invoke(main, ["fetch", "--config", str(config_path)])

    assert result.exit_code == 2
    assert "No such command 'fetch'" in result.output


def test_accounts_command_is_removed(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path)

    result = CliRunner().invoke(main, ["accounts", "--config", str(config_path)])

    assert result.exit_code == 2
    assert "No such command 'accounts'" in result.output


def test_brief_runs_scan_pipeline_without_api(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    scan_dir = tmp_path / "timeline_scans"
    output_path = tmp_path / "brief.md"
    scan_dir.mkdir()
    write_config(config_path)

    captured: dict[str, object] = {}

    async def fake_run_scan_pipeline(config_path_arg, hours, scan_dir_arg, skip_dedup, output_file) -> None:
        captured["config_path"] = config_path_arg
        captured["hours"] = hours
        captured["scan_dir"] = scan_dir_arg
        captured["skip_dedup"] = skip_dedup
        captured["output_file"] = output_file

    monkeypatch.setattr(cli_module, "_run_scan_pipeline", fake_run_scan_pipeline)

    result = CliRunner().invoke(
        main,
        [
            "brief",
            "--config",
            str(config_path),
            "--hours",
            "12",
            "--scan-dir",
            str(scan_dir),
            "--skip-dedup",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "config_path": str(config_path),
        "hours": 12,
        "scan_dir": scan_dir,
        "skip_dedup": True,
        "output_file": str(output_path),
    }


def test_run_runs_scan_pipeline_without_api(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path)

    captured: dict[str, object] = {}

    async def fake_run(config_path_arg, hours, scan_dir_arg, skip_dedup, output_file) -> None:
        captured["config_path"] = config_path_arg
        captured["hours"] = hours
        captured["scan_dir"] = scan_dir_arg
        captured["skip_dedup"] = skip_dedup
        captured["output_file"] = output_file

    monkeypatch.setattr(cli_module, "_run", fake_run)

    result = CliRunner().invoke(main, ["run", "--config", str(config_path)])

    assert result.exit_code == 0
    assert captured == {
        "config_path": str(config_path),
        "hours": 36,
        "scan_dir": None,
        "skip_dedup": False,
        "output_file": None,
    }


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
