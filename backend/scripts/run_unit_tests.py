import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = "postgresql+psycopg://corvus:password@localhost:5432/corvus"


def main() -> int:
    environment = os.environ.copy()
    environment.setdefault("CORVUS_DATABASE_URL", TEST_DATABASE_URL)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-m",
            "not integration",
            "-p",
            "no:cacheprovider",
        ],
        cwd=BACKEND_DIR,
        env=environment,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
