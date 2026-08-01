"""One-off: copy the local SQLite catalogue into the configured Supabase database.

Local development built the catalogue in SQLite. Supabase starts with only the
rows that data migrations create, so the live shop looks almost empty. This dumps
the local data and loads it into Supabase.

Usage (from the project root):
    python bin/sync_local_to_supabase.py

Reads DATABASE_URL from .env for the destination. Nothing is printed that
contains credentials.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DUMP_PATH = BASE_DIR / "local_catalogue_dump.json"

# Content types and permissions are recreated per database; sessions and admin
# logs are throwaway. Everything else (catalogue, CMS, users) travels.
EXCLUDES = (
    "contenttypes",
    "auth.permission",
    "sessions",
    "admin.logentry",
)


def run(args: list[str], env: dict[str, str]) -> None:
    result = subprocess.run(args, env=env, cwd=BASE_DIR, text=True)
    if result.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(args[:3])}...")


def main() -> None:
    base_env = dict(os.environ)
    base_env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    # Product copy contains emoji; the Windows console codec would otherwise fail.
    base_env["PYTHONIOENCODING"] = "utf-8"
    base_env["PYTHONUTF8"] = "1"

    # Source: force SQLite by blanking the Postgres URLs for this process only.
    sqlite_env = dict(base_env)
    sqlite_env["DATABASE_URL"] = ""
    sqlite_env["SUPABASE_DB_URL"] = ""

    dump_args = [
        sys.executable,
        "manage.py",
        "dumpdata",
        "--natural-foreign",
        "--indent",
        "1",
        "--output",
        str(DUMP_PATH),
    ]
    for label in EXCLUDES:
        dump_args += ["--exclude", label]

    print("Dumping local SQLite data...")
    run(dump_args, sqlite_env)
    size_kb = DUMP_PATH.stat().st_size / 1024
    print(f"Wrote {DUMP_PATH.name} ({size_kb:.0f} KB)")

    # Destination: the .env DATABASE_URL (Supabase).
    print("Clearing destination tables...")
    run([sys.executable, "manage.py", "flush", "--noinput"], base_env)

    print("Loading data into Supabase...")
    run([sys.executable, "manage.py", "loaddata", str(DUMP_PATH)], base_env)

    print("Done. Verify counts with a quick shell query.")


if __name__ == "__main__":
    main()
