import re

def classify_market(m):
    text=' '.join(str(m.get(k,'')) for k in ['ticker','event_ticker','title','yes_sub_title','no_sub_title']).lower()
    if any(x in text for x in ['tennis','atp','wta','challenger','itf']): return 'Tennis'
    if any(x in text for x in ['mlb','baseball','yankees','dodgers','mets','red sox','cubs','braves','padres','giants','rangers','astros','phillies']): return 'MLB'
    if any(x in text for x in ['college football','ncaa football','cfb','fbs','bulldogs','tigers','buckeyes','wolverines','crimson tide','fighting irish','longhorns']): return 'CFB'
    return 'Other'

def market_prob(m):
    # Prefer executable YES ask if available; otherwise use last price, then bid.
    for k in ['yes_ask_dollars','last_price_dollars','yes_bid_dollars']:
        v=m.get(k)
        if v is not None:
            try: return float(v)
            except ValueError: pass
    return None

def side_text(m):
    return str(m.get('yes_sub_title') or m.get('title') or 'YES')
