import requests

from edge.config import BASE_URL, USER_AGENT


class KalshiClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

        self.s = requests.Session()

        self.s.headers.update(
            {
                "User-Agent": USER_AGENT
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

    def _is_combo_market(self, market):
        """
        Reject giant cross-category / parlay-style Kalshi markets.
        """

        ticker = str(
            market.get("ticker") or ""
        ).upper()

        event_ticker = str(
            market.get("event_ticker") or ""
        ).upper()

        title = str(
            market.get("title") or ""
        ).lower()

        subtitle = str(
            market.get("subtitle") or ""
        ).lower()

        text = f"{title} {subtitle}"

        # Known combo / shard families.
        blocked_ticker_terms = [
            "CROSSCATEGORY",
            "SHARD",
            "PARLAY",
            "MULTILEG",
        ]

        if any(
            term in ticker
            or term in event_ticker
            for term in blocked_ticker_terms
        ):
            return True

        # Giant comma-separated YES/NO lists.
        if title.count(",") >= 3:
            return True

        if text.count("yes ") >= 3:
            return True

        if text.count("no ") >= 3:
            return True

        if len(title) > 220:
            return True

        return False

    def all_open_markets(
    self,
    max_items=300,
    max_pages=8,
):
    import time

    out = []
    cursor = None
    pages = 0

    while len(out) < max_items and pages < max_pages:
        pages += 1

        try:
            data = self.markets(
                status="open",
                limit=100,
                cursor=cursor,
            )

        except requests.HTTPError as e:
            response = getattr(e, "response", None)

            if response is not None and response.status_code == 429:
                break

            raise

        markets = data.get("markets", [])

        for market in markets:
            if self._is_combo_market(market):
                continue

            out.append(market)

            if len(out) >= max_items:
                break

        cursor = data.get("cursor")

        if not cursor:
            break

        time.sleep(1.0)

    return out[:max_items]
    def orderbook(self, ticker):
        r = self.s.get(
            f"{self.base_url}/markets/{ticker}/orderbook",
            timeout=20,
        )

        r.raise_for_status()

        return r.json()