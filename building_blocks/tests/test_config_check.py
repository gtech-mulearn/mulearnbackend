from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from building_blocks import config

ROOT = Path(__file__).resolve().parents[2]


def env_file(tmp_path, drop=(), **values):
    """.env.sample with some lines dropped and some values set."""
    lines = []
    for line in (ROOT / ".env.sample").read_text(encoding="utf-8").splitlines():
        name = line.split("=", 1)[0].strip()
        if name in drop or name in values:
            continue
        lines.append(line)
    lines += [f"{name}={value}" for name, value in values.items()]
    path = tmp_path / ".env.check"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_the_sample_env_file_is_valid(tmp_path, capsys):
    call_command("config_check", "--env-file", str(env_file(tmp_path)))

    assert "every declared setting is valid for local" in capsys.readouterr().out


def test_every_problem_is_reported_in_one_run(tmp_path, capsys):
    path = env_file(
        tmp_path,
        drop=("SECRET_KEY", "BACKEND_API_KEY"),
        MULEARN_ENV="production",
        EMAIL_PORT="five-eight-seven",
        R2_PUBLIC_BASE_URL="files.example.com",
    )

    with pytest.raises(SystemExit) as exit_:
        call_command("config_check", "--env-file", str(path))

    err = capsys.readouterr().err
    assert exit_.value.code == 1
    assert "SECRET_KEY is required in production but isn't set." in err
    assert "BACKEND_API_KEY is required in production but isn't set." in err
    assert "EMAIL_PORT must be a whole number, not 'five-eight-seven'." in err
    assert "R2_PUBLIC_BASE_URL must be an http or https URL with a host" in err
    assert "4 problem(s) in .env.check for production." in err


def test_no_secret_value_is_printed(tmp_path, capsys):
    secrets = [name for name, setting in config.declared().items() if setting.secret]
    values = {name: f"secret-{name.lower()}-value" for name in secrets}
    path = env_file(tmp_path, EMAIL_PORT="bad", MULEARN_ENV="staging", **values)

    with pytest.raises(SystemExit):
        call_command("config_check", "--env-file", str(path))

    output = "".join(capsys.readouterr())
    assert secrets
    assert not [value for value in values.values() if value in output]


def test_an_invalid_mulearn_env_is_a_problem(tmp_path, capsys):
    with pytest.raises(SystemExit):
        call_command("config_check", "--env-file", str(env_file(tmp_path, MULEARN_ENV="prod")))

    assert "MULEARN_ENV must be one of local, dev, staging, production, not 'prod'." in capsys.readouterr().err


def test_a_missing_file_is_an_error(tmp_path):
    with pytest.raises(CommandError, match="No env file"):
        call_command("config_check", "--env-file", str(tmp_path / "absent.env"))
