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
    "mve_filter": "exclude",
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
        max_pages=20,
    ):
        import time

        out = []
        cursor = None
        pages = 0

        while len(out) < max_items and pages < max_pages:
            pages += 20

            data = self.markets(
                status="open",
                limit=100,
                cursor=cursor,
            )

            markets = data.get("markets", [])

            for market in markets:
                ticker = str(market.get("ticker") or "").upper()
                event_ticker = str(market.get("event_ticker") or "").upper()

                if (
                    "CROSSCATEGORY" in ticker
                    or "CROSSCATEGORY" in event_ticker
                    or "SHARD" in ticker
                    or "SHARD" in event_ticker
                ):
                    continue

                yes_ask = market.get("yes_ask")
                yes_bid = market.get("yes_bid")
                last_price = market.get("last_price")

                yes_ask_dollars = market.get("yes_ask_dollars")
                yes_bid_dollars = market.get("yes_bid_dollars")
                last_price_dollars = market.get("last_price_dollars")

                has_price = any(
                    value not in (None, 0, 0.0, "0", "0.0000")
                    for value in [
                        yes_ask,
                        yes_bid,
                        last_price,
                        yes_ask_dollars,
                        yes_bid_dollars,
                        last_price_dollars,
                    ]
                )

                if not has_price:
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