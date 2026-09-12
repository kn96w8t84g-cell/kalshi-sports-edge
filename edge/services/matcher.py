import re
import unicodedata
from difflib import SequenceMatcher


STOPWORDS = {
    "the", "a", "an", "and", "or", "vs", "v", "at",
    "to", "of", "for", "in", "on", "will", "win",
    "game", "match", "market", "yes", "no"
}


ALIASES = {
    # MLB common aliases
    "ny yankees": "new york yankees",
    "yankees": "new york yankees",
    "ny mets": "new york mets",
    "mets": "new york mets",
    "la dodgers": "los angeles dodgers",
    "dodgers": "los angeles dodgers",
    "la angels": "los angeles angels",
    "angels": "los angeles angels",
    "sf giants": "san francisco giants",
    "giants": "san francisco giants",
    "sd padres": "san diego padres",
    "padres": "san diego padres",
    "boston red sox": "boston red sox",
    "red sox": "boston red sox",
    "white sox": "chicago white sox",
    "cubs": "chicago cubs",

    # College football/common short forms
    "ohio state": "ohio state",
    "osu": "ohio state",
    "michigan": "michigan",
    "alabama": "alabama",
    "bama": "alabama",
    "georgia": "georgia",
    "usc": "usc",
    "ucla": "ucla",
    "lsu": "lsu",
    "texas": "texas",
    "texas a&m": "texas a m",
    "texas am": "texas a m",
    "notre dame": "notre dame",
}


def norm(s):
    if s is None:
        return ""

    s = str(s).strip().lower()

    # Remove accents so names such as "Moutet" / accented tennis
    # names compare more consistently.
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))

    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = " ".join(s.split())

    return ALIASES.get(s, s)


def tokens(s):
    return [
        x for x in norm(s).split()
        if x not in STOPWORDS and len(x) > 1
    ]


def token_overlap(a, b):
    a_tokens = set(tokens(a))
    b_tokens = set(tokens(b))

    if not a_tokens or not b_tokens:
        return 0.0

    overlap = len(a_tokens & b_tokens)
    return overlap / max(1, min(len(a_tokens), len(b_tokens)))


def name_score(text, name):
    """
    Score how likely a team/player name appears inside a Kalshi title.

    1.00 = direct full-name containment
    high score = strong token/name similarity
    low score = weak/unrelated match
    """

    t = norm(text)
    n = norm(name)

    if not t or not n:
        return 0.0

    # Strongest case: exact normalized name appears in market text.
    if n in t:
        return 1.0

    # Also consider aliases/shortened forms word-by-word.
    ntokens = tokens(n)
    ttokens = tokens(t)

    if ntokens and all(tok in ttokens for tok in ntokens):
        return 0.97

    overlap = token_overlap(t, n)

    # Compare against chunks of the title instead of comparing a short
    # player's name against the entire long Kalshi sentence.
    words = t.split()
    n_words = max(1, len(n.split()))
    chunk_scores = []

    for size in range(max(1, n_words - 1), min(len(words), n_words + 2) + 1):
        for i in range(0, len(words) - size + 1):
            chunk = " ".join(words[i:i + size])
            chunk_scores.append(
                SequenceMatcher(None, chunk, n).ratio()
            )

    chunk_similarity = max(chunk_scores) if chunk_scores else 0.0
    whole_similarity = SequenceMatcher(None, t, n).ratio()

    # Token overlap matters more than whole-sentence fuzzy similarity.
    return max(
        whole_similarity * 0.70,
        chunk_similarity,
        overlap * 0.95,
    )


def best_names(text, names, threshold=0.55):
    """
    Return the single best matching name.
    """

    scores = []

    for name in names:
        if not name:
            continue

        score = name_score(text, name)
        scores.append((score, name))

    scores.sort(key=lambda x: x[0], reverse=True)

    if not scores:
        return None

    score, name = scores[0]

    return name if score >= threshold else None


def find_two(text, names, threshold=0.55):
    """
    Return the two most likely unique teams/players found in a market title.

    Designed for titles such as:
      "Will Carlos Alcaraz defeat Jannik Sinner?"
      "Yankees vs Red Sox"
      "Will Ohio State beat Michigan?"
    """

    scored = []

    seen_normalized = set()

    for name in names:
        if not name:
            continue

        n = norm(name)

        if not n or n in seen_normalized:
            continue

        seen_normalized.add(n)

        score = name_score(text, name)

        if score >= threshold:
            scored.append((score, name))

    scored.sort(key=lambda x: x[0], reverse=True)

    unique = []

    for score, name in scored:
        normalized = norm(name)

        # Prevent the same entity from appearing twice through slightly
        # different spellings.
        duplicate = False

        for existing in unique:
            if (
                normalized == norm(existing)
                or SequenceMatcher(
                    None,
                    normalized,
                    norm(existing)
                ).ratio() > 0.94
            ):
                duplicate = True
                break

        if not duplicate:
            unique.append(name)

        if len(unique) == 2:
            break

    return unique