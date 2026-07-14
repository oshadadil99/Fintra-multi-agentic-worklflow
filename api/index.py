"""Vercel serverless entrypoint - exposes the FastAPI app.

Vercel's Python runtime looks for `app` in api/index.py; all routes are
rewritten here by vercel.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fintra.api.app import app  # noqa: E402, F401
