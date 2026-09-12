import time
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
        max_pages=5,
    ):
        """
        Fetch normal open Kalshi markets while excluding
        multivariate/combo markets at the API level.
        """

        out = []
        cursor = None
        pages = 0

        while (
            len(out) < max_items
            and pages < max_pages
        ):
            pages += 1

            try:
                data = self.markets(
                    status="open",
                    limit=min(
                        100,
                        max_items - len(out),
                    ),
                    cursor=cursor,
                )

            except requests.HTTPError as e:
                response = getattr(
                    e,
                    "response",
                    None,
                )

                if (
                    response is not None
                    and response.status_code == 429
                ):
                    raise

                raise

            markets = data.get(
                "markets",
                [],
            )

            out.extend(markets)

            cursor = data.get("cursor")

            if not cursor:
                break

            time.sleep(0.75)

        return out[:max_items]

    def orderbook(self, ticker):
        r = self.s.get(
            f"{self.base_url}/markets/{ticker}/orderbook",
            timeout=20,
        )

        r.raise_for_status()
        return r.json()