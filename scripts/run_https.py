"""Пилотный HTTPS-сервер API (НФТ-06)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.make_certs import make_certs


def main() -> None:
    cert, key = make_certs()
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8443",
                "--ssl-certfile",
                str(cert),
                "--ssl-keyfile",
                str(key),
            ]
        )
    )


if __name__ == "__main__":
    main()
