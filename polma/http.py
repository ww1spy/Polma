"""Shared HTTP session with retries — public APIs flake; cycles must not."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 20


def make_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    session.mount("https://", adapter)
    return session


SESSION = make_session()


def get_json(url, params=None):
    resp = SESSION.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
