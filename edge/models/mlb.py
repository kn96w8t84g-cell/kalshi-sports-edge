from edge.models.common import clamp

def estimate(home_strength=0, away_strength=0, starter_diff=0, bullpen_diff=0, offense_diff=0):
    # Features are differences in standardized units. Home field gets a modest prior.
    score=0.35 + 0.55*home_strength + 0.9*starter_diff + 0.35*bullpen_diff + 0.45*offense_diff
    import math
    p=1/(1+math.exp(-score))
    quality=0.62 + min(0.25, abs(score)*0.08)
    return clamp(p), min(0.90,quality)
