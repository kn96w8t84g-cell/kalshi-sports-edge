import math

def clamp(p, lo=0.02, hi=0.98): return max(lo,min(hi,p))
def logistic(x): return 1/(1+math.exp(-x))
def elo_prob(r1,r2): return 1/(1+10**((r2-r1)/400))
def edge_score(model, market): return model-market

def verdict(model, market, quality, min_edge=0.07, min_conf=0.58):
    if model is None or market is None or quality < 0.55: return 'PASS'
    e=model-market
    if model>=min_conf and e>=min_edge and quality>=0.70: return 'STRONG'
    if e>=min_edge/2 and quality>=0.60: return 'WATCH'
    return 'PASS'
