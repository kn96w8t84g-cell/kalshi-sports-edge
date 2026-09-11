from edge.models.common import clamp

def estimate(player_a, player_b, form_a=None, form_b=None, rank_a=None, rank_b=None, surface_bonus=0.0):
    # Conservative transparent baseline. Positive values favor A.
    score=surface_bonus
    if rank_a and rank_b: score += (rank_b-rank_a)*0.035
    if form_a is not None and form_b is not None: score += (form_a-form_b)*1.25
    # score is intentionally compressed to avoid fake certainty.
    p=0.5 + 0.22*(__import__('math').tanh(score/5))
    quality=0.72 if (rank_a and rank_b and form_a is not None and form_b is not None) else 0.55
    return clamp(p), quality
