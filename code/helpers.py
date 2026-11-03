"""Code shared by more than one stage: project paths and HTTP downloads."""

from __future__ import annotations

import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
FIGURES = ROOT / "figures"

HEADERS = {"User-Agent": "Mozilla/5.0 (academic project; HEC Lausanne)"}


def download(url: str, retries: int = 4, timeout: float = 60.0) -> bytes:
    """GET a URL and return its body, retrying transient failures with backoff."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"download failed after {retries} tries: {url}") from exc
            time.sleep(5 * 2 ** attempt)
