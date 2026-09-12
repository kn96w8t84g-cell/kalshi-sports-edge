import re


def _text_parts(m):
    return [
        str(m.get("title") or ""),
        str(m.get("subtitle") or ""),
        str(m.get("yes_sub_title") or ""),
        str(m.get("no_sub_title") or ""),
        str(m.get("ticker") or ""),
        str(m.get("event_ticker") or ""),
    ]


def _market_text(m):
    return " ".join(_text_parts(m)).lower()


def _looks_like_parlay_or_combo(text):
    """
    Reject giant combo/parlay style markets that contain many unrelated teams.
    """

    separators = [
        ",yes ",
        ",no ",
        " parlay ",
        " same game parlay ",
    ]

    if any(x in text for x in separators):
        return True

    # Very long titles with lots of commas are usually combo-style markets.
    if len(text) > 220 and text.count(",") >= 3:
        return True

    # Too many repeated yes/no clauses usually means many legs.
    if text.count(" yes ") >= 3 or text.count(" no ") >= 3:
        return True

    return False


def classify_market(m):
    text = _market_text(m)

    # Ignore giant combo/parlay markets.
    if _looks_like_parlay_or_combo(text):
        return "Other"

    # -------------------------
    # TENNIS
    # -------------------------
    tennis_terms = [
        "tennis",
        "atp",
        "wta",
        "challenger",
        "itf",
        "us open",
        "australian open",
        "french open",
        "roland garros",
        "wimbledon",
    ]

    if any(term in text for term in tennis_terms):
        return "Tennis"

    # -------------------------
    # MLB
    # -------------------------
    mlb_terms = [
        "mlb",
        "major league baseball",
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

    mlb_hits = sum(1 for term in mlb_terms if term in text)

    # Require a baseball signal or at least 2 MLB team signals.
    if (
        "mlb" in text
        or "baseball" in text
        or "major league baseball" in text
        or mlb_hits >= 2
    ):
        return "MLB"

    # -------------------------
    # COLLEGE FOOTBALL
    # -------------------------
    cfb_terms = [
        "college football",
        "ncaa football",
        "cfb",
        "fbs",
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
        "razorbacks",
    ]

    cfb_hits = sum(1 for term in cfb_terms if term in text)

    if (
        "college football" in text
        or "ncaa football" in text
        or "cfb" in text
        or cfb_hits >= 2
    ):
        return "CFB"

    return "Other"


def market_prob(m):
    """
    Return the best available YES probability as 0.00 - 1.00.
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

                if 0 <= value <= 100:
                    return value / 100.0
            except (TypeError, ValueError):
                pass

    return None


def side_text(m):
    """
    Prefer the explicit YES-side label when Kalshi provides one.
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
    Build one clean matchup string for matching.
    """

    parts = [
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

    text = re.sub(r"\s+", " ", text).strip()

    return text