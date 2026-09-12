import math
import pandas as pd

from datetime import date, datetime, timezone

from edge.connectors.kalshi import KalshiClient
from edge.connectors.mlb import MLBClient
from edge.connectors.cfb import CFBClient
from edge.connectors.tennis import load_matches, recent_player_form

from edge.services.kalshi_parser import (
    classify_market,
    market_prob,
    side_text,
)

from edge.services.matcher import find_two
from edge.models.common import verdict, clamp
from edge.models import tennis as tennis_model
from edge.config import CFBD_API_KEY


def _market_rows(markets):
    rows = []

    debug_counts = {
        "total": 0,
        "other": 0,
        "no_price": 0,
        "usable": 0,
    }

    for m in markets:
        debug_counts["total"] += 1

        sport = classify_market(m)

        if sport == "Other":
            debug_counts["other"] += 1
            continue

        p = market_prob(m)

        if p is None:
            debug_counts["no_price"] += 1
            continue

        debug_counts["usable"] += 1

        rows.append(
            {
                "ticker": m.get("ticker"),
                "event_ticker": m.get("event_ticker"),
                "market_title": m.get("title") or side_text(m),
                "side": side_text(m),
                "sport": sport,
                "market_prob": p,
                "volume": (
                    m.get("volume_24h_fp")
                    or m.get("volume_fp")
                    or m.get("volume")
                    or 0
                ),
                "close_time": m.get("close_time"),
            }
        )

    print("MARKET DEBUG:", debug_counts)

    return rows

def _yes_entity(text, hits):
    """
    Determine which matched team/player corresponds to YES.
    """

    if not hits:
        return None

    low = str(text).lower()

    contained = [
        h for h in hits
        if str(h).lower() in low
    ]

    if contained:
        return max(contained, key=len)

    return hits[0]


def _safe_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# MLB
# ============================================================

def build_mlb_rows(rows):
    if not rows:
        return []

    try:
        client = MLBClient()
        sched = client.schedule()
    except Exception:
        return []

    games = []

    for d in sched.get("dates", []):
        games.extend(d.get("games", []))

    if not games:
        return []

    team_names = []
    team_ids = {}
    game_pairs = []

    for g in games:
        try:
            away = g["teams"]["away"]["team"]
            home = g["teams"]["home"]["team"]

            away_name = away["name"]
            home_name = home["name"]

            team_names.extend([away_name, home_name])

            team_ids[away_name] = away["id"]
            team_ids[home_name] = home["id"]

            game_pairs.append(
                {
                    "away": away_name,
                    "home": home_name,
                    "game": g,
                }
            )

        except Exception:
            continue

    stats = {}

    for team_name, team_id in team_ids.items():
        try:
            payload = client.team_stats(team_id)

            flat = {}

            for group in payload.get("stats", []):
                for split in group.get("splits", []):
                    stat = split.get("stat", {})

                    for key, value in stat.items():
                        if key not in flat:
                            flat[key] = value

            stats[team_name] = flat

        except Exception:
            stats[team_name] = {}

    out = []

    for r in rows:
        if r["sport"] != "MLB":
            continue

        hits = find_two(
            r["market_title"],
            team_names,
            threshold=0.55,
        )

        if len(hits) < 2:
            continue

        yes = _yes_entity(
            r["side"] + " " + r["market_title"],
            hits,
        )

        if not yes:
            continue

        other = hits[1] if hits[0] == yes else hits[0]

        yes_stats = stats.get(yes, {})
        other_stats = stats.get(other, {})

        yes_is_home = None

        for pair in game_pairs:
            teams = {pair["away"], pair["home"]}

            if yes in teams and other in teams:
                yes_is_home = yes == pair["home"]
                break

        yes_ops = _safe_float(
            yes_stats.get("ops"),
            0.720,
        )

        other_ops = _safe_float(
            other_stats.get("ops"),
            0.720,
        )

        yes_era = _safe_float(
            yes_stats.get("era"),
            4.20,
        )

        other_era = _safe_float(
            other_stats.get("era"),
            4.20,
        )

        ops_diff = yes_ops - other_ops

        # Lower ERA is better.
        era_diff = other_era - yes_era

        home_bonus = 0

        if yes_is_home is True:
            home_bonus = 0.15
        elif yes_is_home is False:
            home_bonus = -0.15

        score = (
            home_bonus
            + (2.2 * ops_diff)
            + (0.18 * era_diff)
        )

        p = 1 / (1 + math.exp(-score))

        enough_stats = bool(yes_stats and other_stats)

        quality = 0.72 if enough_stats else 0.50

        location = ""

        if yes_is_home is True:
            location = " YES team is home."
        elif yes_is_home is False:
            location = " YES team is away."

        r.update(
            model_prob=clamp(p),
            data_quality=quality,
            analysis_status="ANALYZED",
            matchup=f"{yes} vs {other}",
            reason=(
                f"MLB model: season OPS + ERA comparison."
                f" YES mapped to {yes}.{location}"
            ),
        )

        out.append(r)

    return out


# ============================================================
# TENNIS
# ============================================================

def _latest_rank(df, player):
    """
    Find the most recent available ranking for a tennis player.
    """

    try:
        matches = df[
            (df["winner_name"] == player)
            | (df["loser_name"] == player)
        ].copy()

        if matches.empty:
            return None

        matches = matches.sort_values(
            "tourney_date",
            ascending=False,
        )

        for _, row in matches.iterrows():

            if row.get("winner_name") == player:
                rank = _safe_float(row.get("winner_rank"))

            else:
                rank = _safe_float(row.get("loser_rank"))

            if rank is not None and rank > 0:
                return rank

    except Exception:
        pass

    return None


def _head_to_head(df, player_a, player_b):
    """
    Return head-to-head wins from available season data.
    """

    try:
        h2h = df[
            (
                (df["winner_name"] == player_a)
                & (df["loser_name"] == player_b)
            )
            |
            (
                (df["winner_name"] == player_b)
                & (df["loser_name"] == player_a)
            )
        ]

        a_wins = int(
            (h2h["winner_name"] == player_a).sum()
        )

        b_wins = int(
            (h2h["winner_name"] == player_b).sum()
        )

        return a_wins, b_wins

    except Exception:
        return 0, 0


def build_tennis_rows(rows):
    if not rows:
        return []

    out = []
    cache = {}

    for r in rows:
        if r["sport"] != "Tennis":
            continue

        found = None

        for tour in ["ATP", "WTA"]:

            try:
                if tour not in cache:
                    cache[tour] = load_matches(tour)

                df = cache[tour]

                names = pd.unique(
                    pd.concat(
                        [
                            df["winner_name"],
                            df["loser_name"],
                        ]
                    )
                ).tolist()

                hits = find_two(
                    r["market_title"],
                    names,
                    threshold=0.55,
                )

                if len(hits) >= 2:
                    found = (tour, df, hits)
                    break

            except Exception:
                continue

        if not found:
            continue

        tour, df, hits = found

        yes = _yes_entity(
            r["side"] + " " + r["market_title"],
            hits,
        )

        if not yes:
            continue

        other = hits[1] if hits[0] == yes else hits[0]

        form_yes = recent_player_form(
            df,
            yes,
            10,
        )

        form_other = recent_player_form(
            df,
            other,
            10,
        )

        if (
            form_yes["win_rate"] is None
            or form_other["win_rate"] is None
        ):
            continue

        rank_yes = _latest_rank(df, yes)
        rank_other = _latest_rank(df, other)

        p, quality = tennis_model.estimate(
            yes,
            other,
            form_yes["win_rate"],
            form_other["win_rate"],
            rank_yes,
            rank_other,
        )

        h2h_yes, h2h_other = _head_to_head(
            df,
            yes,
            other,
        )

        h2h_total = h2h_yes + h2h_other

        if h2h_total >= 2:
            h2h_rate = h2h_yes / h2h_total

            adjustment = (
                h2h_rate - 0.5
            ) * 0.05

            p = clamp(p + adjustment)

        if (
            form_yes["matches"] >= 5
            and form_other["matches"] >= 5
            and rank_yes
            and rank_other
        ):
            quality = max(quality, 0.72)

        elif (
            form_yes["matches"] >= 5
            and form_other["matches"] >= 5
        ):
            quality = max(quality, 0.62)

        else:
            quality = min(quality, 0.54)

        rank_text = ""

        if rank_yes and rank_other:
            rank_text = (
                f" Rankings: {yes} #{int(rank_yes)},"
                f" {other} #{int(rank_other)}."
            )

        h2h_text = ""

        if h2h_total:
            h2h_text = (
                f" Season H2H: {h2h_yes}-{h2h_other}."
            )

        r.update(
            model_prob=p,
            data_quality=quality,
            analysis_status="ANALYZED",
            matchup=f"{yes} vs {other}",
            reason=(
                f"{tour} model: recent form "
                f"{form_yes['wins']}-{form_yes['losses']} vs "
                f"{form_other['wins']}-{form_other['losses']}."
                f"{rank_text}{h2h_text}"
            ),
        )

        out.append(r)

    return out


# ============================================================
# COLLEGE FOOTBALL
# ============================================================

def build_cfb_rows(rows):
    if not rows:
        return []

    if not CFBD_API_KEY:
        return []

    try:
        client = CFBClient()

        games = client.games(date.today().year) or []
        ratings_raw = client.ratings(date.today().year) or []

    except Exception:
        return []

    names = []

    for g in games:
        home = g.get("home_team")
        away = g.get("away_team")

        if home:
            names.append(home)

        if away:
            names.append(away)

    ratings = {}

    for item in ratings_raw:
        team = item.get("team")

        if not team:
            continue

        rating = _safe_float(item.get("rating"))

        if rating is not None:
            ratings[team] = rating

    out = []

    for r in rows:

        if r["sport"] != "CFB":
            continue

        hits = find_two(
            r["market_title"],
            names,
            threshold=0.55,
        )

        if len(hits) < 2:
            continue

        yes = _yes_entity(
            r["side"] + " " + r["market_title"],
            hits,
        )

        if not yes:
            continue

        other = hits[1] if hits[0] == yes else hits[0]

        yes_rating = ratings.get(yes)
        other_rating = ratings.get(other)

        if (
            yes_rating is None
            or other_rating is None
        ):
            continue

        yes_home = None

        for g in games:

            home = g.get("home_team")
            away = g.get("away_team")

            if {home, away} == {yes, other}:
                yes_home = home == yes
                break

        rating_diff = yes_rating - other_rating

        home_bonus = 0

        if yes_home is True:
            home_bonus = 0.18

        elif yes_home is False:
            home_bonus = -0.18

        score = (
            0.06 * rating_diff
            + home_bonus
        )

        p = 1 / (1 + math.exp(-score))

        quality = 0.74

        location = ""

        if yes_home is True:
            location = " YES team is home."

        elif yes_home is False:
            location = " YES team is away."

        r.update(
            model_prob=clamp(p),
            data_quality=quality,
            analysis_status="ANALYZED",
            matchup=f"{yes} vs {other}",
            reason=(
                f"CFB model: independent team rating comparison."
                f" Rating difference={rating_diff:.1f}."
                f"{location}"
            ),
        )

        out.append(r)

    return out


# ============================================================
# FINAL EDGE BOARD
# ============================================================

def build_edge_board(
    min_edge=0.07,
    min_conf=0.58,
    max_markets=300,
):
    markets = KalshiClient().all_open_markets(
        max_markets
    )

    rows = _market_rows(markets)

    by = {
        "MLB": [],
        "CFB": [],
        "Tennis": [],
    }

    for r in rows:
        if r["sport"] in by:
            by[r["sport"]].append(r)

    tennis_rows = build_tennis_rows(
        by["Tennis"]
    )

    mlb_rows = build_mlb_rows(
        by["MLB"]
    )

    cfb_rows = build_cfb_rows(
        by["CFB"]
    )

    combined = (
        tennis_rows
        + mlb_rows
        + cfb_rows
    )

    seen = {
        x.get("ticker")
        for x in combined
    }

    for r in rows:

        if r.get("ticker") in seen:
            continue

        sport = r.get("sport")

        if sport == "CFB" and not CFBD_API_KEY:
            reason = (
                "CFB market found, but College Football "
                "Data API is not configured. NO DATA."
            )

        elif sport == "Tennis":
            reason = (
                "Tennis market found, but both players "
                "could not be matched to usable current-season "
                "match data. NO DATA."
            )

        elif sport == "MLB":
            reason = (
                "MLB market found, but it could not be "
                "matched to today's MLB schedule/stat data. "
                "NO DATA."
            )

        else:
            reason = (
                "Market found, but no verified independent "
                "sports model was available. NO DATA."
            )

        r.update(
            model_prob=None,
            data_quality=0.0,
            analysis_status="NO_DATA",
            matchup=None,
            reason=reason,
        )

        combined.append(r)

    scan_time = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    for r in combined:

        model_prob = r.get("model_prob")
        market_p = r.get("market_prob")

        if model_prob is None:
            r["edge"] = None
            r["verdict"] = "PASS"
            r["rank_score"] = -1

        else:
            edge = model_prob - market_p

            r["edge"] = edge

            r["verdict"] = verdict(
                model_prob,
                market_p,
                r.get("data_quality", 0),
                min_edge,
                min_conf,
            )

            r["rank_score"] = (
                edge
                + 0.01
                * float(
                    r.get(
                        "data_quality",
                        0,
                    )
                )
            )

        r["last_updated_utc"] = scan_time

    df = pd.DataFrame(combined)

    if df.empty:
        return df

    order = {
        "STRONG": 0,
        "WATCH": 1,
        "PASS": 2,
    }

    df["vorder"] = (
        df["verdict"]
        .map(order)
        .fillna(3)
    )

    df = (
        df.sort_values(
            [
                "vorder",
                "rank_score",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .drop(
            columns=["vorder"]
        )
        .reset_index(drop=True)
    )

    df.insert(
        0,
        "rank",
        range(
            1,
            len(df) + 1,
        ),
    )

    return df