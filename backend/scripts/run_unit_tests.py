import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_JWT_SECRET_KEY = "unit-test-only-secret-key-with-at-least-32-bytes"


def main() -> int:
    environment = os.environ.copy()
    environment.setdefault("CORVUS_DATABASE_URL", TEST_DATABASE_URL)
    environment.setdefault("CORVUS_JWT_SECRET_KEY", TEST_JWT_SECRET_KEY)

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
