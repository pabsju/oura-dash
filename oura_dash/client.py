import time
from datetime import date
from typing import Any, Callable

import httpx

from oura_dash.models import CollectionResponse


class OuraClient:
    def __init__(
        self,
        token: str,
        base_url: str = "https://api.ouraring.com",
        *,
        http: httpx.Client | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._sleep = sleep
        self._http = http or httpx.Client(
            headers={"Authorization": f"Bearer {token}"}, timeout=30.0
        )

    def fetch(self, endpoint: str, start: date, end: date) -> list[dict[str, Any]]:
        params: dict[str, str] = {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        rows: list[dict[str, Any]] = []
        next_token: str | None = None
        while True:
            page_params = dict(params)
            if next_token:
                page_params["next_token"] = next_token
            resp = self._get_with_retry(endpoint, page_params)
            parsed = CollectionResponse.model_validate(resp.json())
            rows.extend(parsed.data)
            if not parsed.next_token:
                return rows
            next_token = parsed.next_token

    def _get_with_retry(self, endpoint: str, params: dict[str, str]) -> httpx.Response:
        url = f"{self._base_url}{endpoint}"
        attempt = 0
        while True:
            resp = self._http.get(url, params=params)
            if resp.status_code == 429 and attempt < self._max_retries:
                retry_after = float(resp.headers.get("Retry-After", "1"))
                self._sleep(retry_after)
                attempt += 1
                continue
            resp.raise_for_status()
            return resp
