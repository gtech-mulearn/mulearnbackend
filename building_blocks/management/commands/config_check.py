"""manage.py config_check --env-file <path>: check an env file before a deploy (issue 0020).

Validates every declared setting (mulearnbackend/config_settings.py) for the file's MULEARN_ENV,
prints every problem in one run, never prints a secret's value, and exits 1 on any problem.
"""

from pathlib import Path

from decouple import RepositoryEnv
from django.core.management.base import BaseCommand, CommandError

from building_blocks import config


class Command(BaseCommand):
    help = "Check every declared setting in an env file for its MULEARN_ENV. Exits 1 on any problem."

    def add_arguments(self, parser):
        parser.add_argument("--env-file", required=True, help="The env file to check, for example .env.production")

    def handle(self, *args, env_file, **options):
        path = Path(env_file)
        if not path.is_file():
            raise CommandError(f"No env file at {path}.")
        source = RepositoryEnv(str(path)).data.get
        try:
            env = config.environment(source)
        except config.ConfigError:
            env = None
        found = config.problems(source)
        if found:
            for problem in found:
                self.stderr.write(f"- {problem}")
            target = env or "an invalid MULEARN_ENV"
            self.stderr.write(f"{len(found)} problem(s) in {path.name} for {target}.")
            raise SystemExit(1)
        self.stdout.write(f"{path.name}: every declared setting is valid for {env}.")
