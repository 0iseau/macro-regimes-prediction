"""Code shared by more than one stage: project paths and HTTP downloads."""

from __future__ import annotations

import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
FIGURES = ROOT / "figures"

def download(url: str, retries: int = 3, timeout: tuple = (10, 30)) -> bytes:
    """GET a URL and return its body, retrying transient failures with backoff.

    The timeout is (connect, read) in seconds: short enough that a blocked
    network fails within about a minute instead of looking frozen.
    """
    for attempt in range(retries):
        try:
            # No custom User-Agent: FRED silently drops custom ones from some
            # networks (e.g. Nuvolos) while answering the requests default.
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"download failed after {retries} tries: {url}") from exc
            time.sleep(2 * 2 ** attempt)
