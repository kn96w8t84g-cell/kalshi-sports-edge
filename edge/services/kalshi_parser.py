import re


def _market_text(m):
    return " ".join(
        str(m.get(k, ""))
        for k in [
            "ticker",
            "event_ticker",
            "title",
            "subtitle",
            "yes_sub_title",
            "no_sub_title",
        ]
    ).lower()


def classify_market(m):
    text = _market_text(m)

    # Tennis
    if any(
        x in text
        for x in [
            "tennis",
            "atp",
            "wta",
            "challenger",
            "itf",
            "us open",
            "australian open",
            "french open",
            "wimbledon",
        ]
    ):
        return "Tennis"

    # MLB / baseball
    mlb_terms = [
        "mlb",
        "baseball",
        "yankees",
        "dodgers",
        "mets",
        "red sox",
        "cubs",
        "braves",
        "padres",
        "giants",
        "rangers",
        "astros",
        "phillies",
        "mariners",
        "orioles",
        "blue jays",
        "rays",
        "guardians",
        "tigers",
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
    ]
    if any(x in text for x in mlb_terms):
        return "MLB"

    # College football
    cfb_terms = [
        "college football",
        "ncaa football",
        "ncaa",
        "cfb",
        "fbs",
        "bulldogs",
        "tigers",
        "buckeyes",
        "wolverines",
        "crimson tide",
        "fighting irish",
        "longhorns",
        "seminoles",
        "nittany lions",
        "ducks",
        "trojans",
        "sooners",
        "aggies",
        "volunteers",
        "hurricanes",
        "razorbacks",
        "wildcats",
    ]
    if any(x in text for x in cfb_terms):
        return "CFB"

    return "Other"


def market_prob(m):
    """
    Return the best available YES probability from Kalshi.
    Values are normalized to 0.00 - 1.00.
    """

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

                if 0 <= value <= 1:
                    return value
            except (ValueError, TypeError):
                pass

    # Fallback for APIs that return cents instead of dollars
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

                if 0 <= value <= 100:
                    return value / 100.0
            except (ValueError, TypeError):
                pass

    return None


def side_text(m):
    """
    Try to extract the actual YES-side team/player instead of
    defaulting to a vague market title.
    """

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
    """
    Build a cleaner text string for matching sports teams/players.
    """

    parts = [
        m.get("title"),
        m.get("subtitle"),
        m.get("yes_sub_title"),
        m.get("no_sub_title"),
    ]

    text = " ".join(str(x) for x in parts if x)

    text = re.sub(r"\s+", " ", text).strip()

    return text