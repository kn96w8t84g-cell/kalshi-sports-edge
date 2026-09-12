from edge.models.common import clamp

def estimate(home_rating=0, away_rating=0, offense_diff=0, defense_diff=0, qb_diff=0):
    score=0.25 + 0.06*(home_rating-away_rating) + 0.35*offense_diff + 0.40*defense_diff + 0.25*qb_diff
    import math
    p=1/(1+math.exp(-score))
    quality=0.60 + min(0.28, abs(score)*0.06)
    return clamp(p), min(0.88,quality)
