"""Shared HTTP session with retries and client-side pacing.

Kalshi throttles request BURSTS from our (shared cloud) egress IP: requests
spaced a few seconds apart succeed while back-to-back ones 429 — even two in
a row. So every request goes through a process-wide pacer (thread-safe, so
the revalidation thread pools respect it too) and 429s back off
exponentially, honoring Retry-After when the server sends it.
"""
import os
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 20
# Max requests/second across the whole process. Override with POLMA_HTTP_RPS.
RPS = float(os.environ.get("POLMA_HTTP_RPS", "4"))


class _Pacer:
    def __init__(self, rps):
        self.interval = 1.0 / rps if rps > 0 else 0.0
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self):
        if not self.interval:
            return
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_at)
            self.next_at = slot + self.interval
        delay = slot - time.monotonic()
        if delay > 0:
            time.sleep(delay)


PACER = _Pacer(RPS)


def make_session():
    session = requests.Session()
    retry = Retry(
        total=6,
        backoff_factor=2.0,          # 2, 4, 8, 16, 32s between attempts
        backoff_max=60,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    session.mount("https://", adapter)
    return session


SESSION = make_session()


def get_json(url, params=None):
    PACER.wait()
    resp = SESSION.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
