import re
from difflib import SequenceMatcher

def norm(s):
    s=str(s).lower()
    s=re.sub(r'[^a-z0-9 ]',' ',s)
    return ' '.join(s.split())

def best_names(text,names,threshold=0.55):
    t=norm(text); scores=[]
    for name in names:
        n=norm(name)
        if n in t or t in n: score=1.0
        else: score=SequenceMatcher(None,t,n).ratio()
        scores.append((score,name))
    scores.sort(reverse=True)
    return scores[0][1] if scores and scores[0][0]>=threshold else None

def find_two(text,names,threshold=0.55):
    t=norm(text); hits=[]
    for name in names:
        n=norm(name)
        score=1.0 if n in t else SequenceMatcher(None,t,n).ratio()
        # direct containment is strongest, and names don't need to match whole title.
        if n in t or score>=threshold: hits.append((score,name))
    hits.sort(reverse=True)
    unique=[]
    for _,name in hits:
        if name not in unique:
            unique.append(name)
        if len(unique)==2: break
    return unique
