import re


def _text_parts(m):
    return [
        str(m.get("title") or ""),
        str(m.get("subtitle") or ""),
        str(m.get("yes_sub_title") or ""),
        str(m.get("no_sub_title") or ""),
        str(m.get("ticker") or ""),
        str(m.get("event_ticker") or ""),

        # Event information added by the Kalshi connector
        str(m.get("_event_title") or ""),
        str(m.get("_event_subtitle") or ""),
        str(m.get("_event_category") or ""),
        str(m.get("_series_ticker") or ""),
    ]


def _market_text(m):
    return " ".join(_text_parts(m)).lower()


def _looks_like_combo(m):
    ticker = str(
        m.get("ticker") or ""
    ).upper()

    event_ticker = str(
        m.get("event_ticker") or ""
    ).upper()

    title = str(
        m.get("title") or ""
    ).lower()

    blocked = [
        "CROSSCATEGORY",
        "MULTILEG",
        "PARLAY",
        "SHARD",
    ]

    if any(
        word in ticker or word in event_ticker
        for word in blocked
    ):
        return True

    if (
        len(title) > 300
        and title.count(",") >= 5
    ):
        return True

    return False


def classify_market(m):
    if _looks_like_combo(m):
        return "Other"

    text = _market_text(m)

    # TENNIS
    tennis_terms = [
        "tennis",
        "atp",
        "wta",
        "challenger",
        "itf",
        "us open tennis",
        "australian open",
        "french open",
        "roland garros",
        "wimbledon",
    ]

    if any(
        term in text
        for term in tennis_terms
    ):
        return "Tennis"

    # MLB
    mlb_terms = [
        "mlb",
        "major league baseball",
        "baseball",
        "yankees",
        "dodgers",
        "mets",
        "red sox",
        "cubs",
        "braves",
        "padres",
        "astros",
        "phillies",
        "mariners",
        "orioles",
        "blue jays",
        "guardians",
        "twins",
        "white sox",
        "royals",
        "athletics",
        "angels",
        "nationals",
        "marlins",
        "brewers",
        "cardinals",
        "pirates",
        "reds",
        "diamondbacks",
        "rockies",
        "giants",
        "rangers",
        "rays",
        "tigers",
    ]

    if any(
        term in text
        for term in mlb_terms
    ):
        return "MLB"

    # COLLEGE FOOTBALL
    cfb_terms = [
        "college football",
        "ncaa football",
        "ncaaf",
        "cfb",
        "fbs",
        "alabama",
        "clemson",
        "ohio state",
        "michigan",
        "georgia",
        "texas a&m",
        "notre dame",
        "usc",
        "ucla",
        "lsu",
        "byu",
        "syracuse",
        "illinois",
        "maryland",
        "minnesota",
        "appalachian st",
        "university at albany",
    ]

    if any(
        term in text
        for term in cfb_terms
    ):
        return "CFB"

    return "Other"


def market_prob(m):
    dollar_fields = [
        "yes_ask_dollars",
        "last_price_dollars",
        "yes_bid_dollars",
    ]

    for key in dollar_fields:
        value = m.get(key)

        if value is not None:
            try:
                value = float(value)

                if 0 < value <= 1:
                    return value

            except (TypeError, ValueError):
                pass

    cent_fields = [
        "yes_ask",
        "last_price",
        "yes_bid",
    ]

    for key in cent_fields:
        value = m.get(key)

        if value is not None:
            try:
                value = float(value)

                if 0 < value <= 100:
                    return value / 100.0

            except (TypeError, ValueError):
                pass

    return None


def side_text(m):
    candidates = [
        m.get("yes_sub_title"),
        m.get("subtitle"),
        m.get("title"),
    ]

    for value in candidates:
        if value:
            value = str(value).strip()

            if value:
                return value

    return "YES"


def clean_market_title(m):
    parts = [
        m.get("_event_title"),
        m.get("title"),
        m.get("subtitle"),
        m.get("yes_sub_title"),
        m.get("no_sub_title"),
    ]

    text = " ".join(
        str(x).strip()
        for x in parts
        if x
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()