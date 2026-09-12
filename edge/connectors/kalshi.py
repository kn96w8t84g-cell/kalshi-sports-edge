import requests

from edge.config import BASE_URL, USER_AGENT


class KalshiClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

        self.s = requests.Session()

        self.s.headers.update(
            {
                "User-Agent": USER_AGENT,
            }
        )

    def markets(
        self,
        status="open",
        limit=100,
        cursor=None,
    ):
        params = {
            "status": status,
            "limit": limit,
        }

        if cursor:
            params["cursor"] = cursor

        r = self.s.get(
            f"{self.base_url}/markets",
            params=params,
            timeout=20,
        )

        r.raise_for_status()

        return r.json()

    def all_open_markets(
        self,
        max_items=300,
        max_pages=1,
    ):
        """
        Temporary simple fetch for debugging.
        Uses one Kalshi request only so errors are visible
        and we avoid repeated rate-limit requests.
        """

        data = self.markets(
            status="open",
            limit=min(100, max_items),
            cursor=None,
        )

        markets = data.get("markets", [])

        return markets[:max_items]

    def orderbook(self, ticker):
        r = self.s.get(
            f"{self.base_url}/markets/{ticker}/orderbook",
            timeout=20,
        )

        r.raise_for_status()

        return r.json()