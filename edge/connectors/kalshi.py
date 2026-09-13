import time
import requests

from edge.config import BASE_URL, USER_AGENT


class KalshiClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update(
            {"User-Agent": USER_AGENT}
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

    def events(
        self,
        status="open",
        limit=200,
        cursor=None,
    ):
        params = {
            "status": status,
            "limit": limit,
            "with_nested_markets": "true",
        }

        if cursor:
            params["cursor"] = cursor

        r = self.s.get(
            f"{self.base_url}/events",
            params=params,
            timeout=20,
        )

        r.raise_for_status()
        return r.json()

    @staticmethod
    def _has_usable_price(market):
        fields = [
            "yes_ask_dollars",
            "yes_bid_dollars",
            "last_price_dollars",
            "yes_ask",
            "yes_bid",
            "last_price",
        ]

        for field in fields:
            value = market.get(field)

            if value is None:
                continue

            try:
                if float(value) > 0:
                    return True
            except (TypeError, ValueError):
                pass

        return False

    def all_open_markets(
        self,
        max_items=300,
        max_pages=20,
    ):
        out = []
        cursor = None
        pages = 0

        while (
            len(out) < max_items
            and pages < max_pages
        ):
            pages += 1

            data = self.events(
                status="open",
                limit=200,
                cursor=cursor,
            )

            events = data.get("events", [])

            if not events:
                break

            for event in events:
                event_title = str(
                    event.get("title") or ""
                ).strip()

                event_subtitle = str(
                    event.get("sub_title") or ""
                ).strip()

                category = str(
                    event.get("category") or ""
                ).strip()

                series_ticker = str(
                    event.get("series_ticker") or ""
                ).strip()

                for market in event.get(
                    "markets", []
                ):
                    if not self._has_usable_price(
                        market
                    ):
                        continue

                    # Preserve event information so
                    # the sports classifier can see it.
                    market = dict(market)

                    market["_event_title"] = (
                        event_title
                    )

                    market["_event_subtitle"] = (
                        event_subtitle
                    )

                    market["_event_category"] = (
                        category
                    )

                    market["_series_ticker"] = (
                        series_ticker
                    )

                    out.append(market)

                    if len(out) >= max_items:
                        break

                if len(out) >= max_items:
                    break

            cursor = data.get("cursor")

            if not cursor:
                break

            time.sleep(0.5)

        return out[:max_items]

    def orderbook(self, ticker):
        r = self.s.get(
            f"{self.base_url}/markets/"
            f"{ticker}/orderbook",
            timeout=20,
        )

        r.raise_for_status()
        return r.json()