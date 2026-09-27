"""Run SQLite evidence tests in a fresh process without caller Settings/dotenv.

Requires the existing requirements-dev.txt environment. No database path or
connection URL is accepted: all application and experiment databases are temporary.
"""

import argparse
import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PYTEST_BOOTSTRAP = """
import sys
if sys.argv.pop(1) == 'fk':
    import sqlite3
    from sqlalchemy import Engine, event
    @event.listens_for(Engine, 'connect')
    def foreign_keys(connection, record):
        if isinstance(connection, sqlite3.Connection):
            connection.execute('PRAGMA foreign_keys=ON')
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Run the full backend suite")
    parser.add_argument("--fk-experiment", action="store_true",
                        help="Enable FK on SQLAlchemy connections in the original suite only")
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    # Inspect source declarations, not Settings itself (whose import reads the environment).
    tree = ast.parse((backend / "app/core/config/settings.py").read_text(encoding="utf-8"))
    fields = {node.target.id.casefold() for node in ast.walk(tree)
              if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}
    environment = {
        key: value for key, value in os.environ.items()
        if key.casefold() not in fields
        and not key.casefold().startswith("pytest")
        and key.casefold() not in {"pythonoptimize", "pythonhome", "pythonstartup"}
    }
    with tempfile.TemporaryDirectory(prefix="hap-sqlite-evidence-") as directory:
        environment.update(
            PYTHONPATH=str(backend), PYTHONDONTWRITEBYTECODE="1",
            DATABASE_URL=f"sqlite:///{Path(directory) / 'bootstrap.db'}",
            BACKUP_AUTO_ENABLED="false", FUND_NAV_AUTO_SYNC_ENABLED="false",
            LOTTERY_DLT_AUTO_SYNC_ENABLED="false", INFRASTRUCTURE_HEALTH_NOTIFY_ENABLED="false",
            PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        )
        tests = backend / "tests"
        target = tests if args.full or args.fk_experiment else tests / "test_sqlite_concurrency.py"
        command = [sys.executable, "-c", PYTEST_BOOTSTRAP,
                   "fk" if args.fk_experiment else "baseline", str(target),
                   "-c", str(backend / "pyproject.toml"),
                   "--basetemp", str(Path(directory) / "pytest"), "-p", "no:cacheprovider", "-s"]
        if args.fk_experiment:
            command += ["--ignore", str(tests / "test_sqlite_concurrency.py")]
        return subprocess.call(command, cwd=directory, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
