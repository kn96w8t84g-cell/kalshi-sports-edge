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

    @staticmethod
    def _normalized_market(market):
        return {
            str(key).strip().lower().replace(" ", "_"): value
            for key, value in market.items()
        }

    @classmethod
    def _is_combo_market(cls, market):
        normalized = cls._normalized_market(market)

        ticker = str(
            normalized.get("ticker") or ""
        ).upper()

        event_ticker = str(
            normalized.get("event_ticker") or ""
        ).upper()

        multivariate_ticker = str(
            normalized.get("multivariate_event_ticker") or ""
        ).upper()

        collection = str(
            normalized.get("mve_collection_ticker") or ""
        ).upper()

        legs = normalized.get("mve_selected_legs")

        text = " ".join(
            [
                ticker,
                event_ticker,
                multivariate_ticker,
                collection,
            ]
        )

        return (
            "CROSSCATEGORY" in text
            or "SHARD" in text
            or "MULTILEG" in text
            or "PARLAY" in text
            or bool(legs)
        )

    @staticmethod
    def _has_usable_price(market):
        values = [
            market.get("yes_ask"),
            market.get("yes_bid"),
            market.get("last_price"),
            market.get("yes_ask_dollars"),
            market.get("yes_bid_dollars"),
            market.get("last_price_dollars"),
        ]

        for value in values:
            if value is None:
                continue

            try:
                if float(value) > 0:
                    return True
            except (TypeError, ValueError):
                continue

        return False

    def all_open_markets(
        self,
        max_items=300,
        max_pages=20,
    ):
        out = []
        cursor = None
        pages = 0

        while len(out) < max_items and pages < max_pages:
            pages += 1

            data = self.markets(
                status="open",
                limit=100,
                cursor=cursor,
            )

            markets = data.get("markets", [])

            if not markets:
                break

            for market in markets:
                if self._is_combo_market(market):
                    continue

                if not self._has_usable_price(market):
                    continue

                out.append(market)

                if len(out) >= max_items:
                    break

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