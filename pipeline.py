import re
import pandas as pd
from datetime import date
from edge.connectors.kalshi import KalshiClient
from edge.connectors.mlb import MLBClient
from edge.connectors.cfb import CFBClient
from edge.connectors.tennis import load_matches, recent_player_form
from edge.services.kalshi_parser import classify_market, market_prob, side_text
from edge.models.common import verdict, clamp
from edge.models import mlb as mlb_model, cfb as cfb_model, tennis as tennis_model
from edge.services.matcher import find_two
from edge.config import CFBD_API_KEY


def _market_rows(markets):
    rows=[]
    for m in markets:
        sport=classify_market(m)
        if sport=='Other': continue
        p=market_prob(m)
        if p is None: continue
        rows.append({'ticker':m.get('ticker'),'event_ticker':m.get('event_ticker'),'market_title':m.get('title') or side_text(m),'side':side_text(m),'sport':sport,'market_prob':p,'volume':m.get('volume_24h_fp') or m.get('volume_fp',0),'close_time':m.get('close_time')})
    return rows

def _yes_entity(text, hits):
    low=text.lower()
    contained=[h for h in hits if str(h).lower() in low]
    return max(contained,key=len) if contained else (hits[0] if hits else None)


def build_mlb_rows(rows):
    try: sched=MLBClient().schedule()
    except Exception: return []
    games=[]
    for d in sched.get('dates',[]): games.extend(d.get('games',[]))
    team_names=[]
    game_map={}
    for g in games:
        away=g['teams']['away']['team']; home=g['teams']['home']['team']
        a,h=away['name'],home['name']; team_names += [a,h]; game_map[(a,h)]=g
    # Season team metrics
    client=MLBClient(); stats={}
    for tid_name in [(g['teams']['away']['team']['id'],g['teams']['away']['team']['name']) for g in games] + [(g['teams']['home']['team']['id'],g['teams']['home']['team']['name']) for g in games]:
        tid,name=tid_name
        if name in stats: continue
        try:
            hit=client.team_stats(tid).get('stats',[])
            flat={}
            for group in hit:
                for split in group.get('splits',[]): flat.update(split.get('stat',{}))
            stats[name]=flat
        except Exception: stats[name]={}
    out=[]
    for r in rows:
        if r['sport']!='MLB': continue
        hits=find_two(r['market_title'],team_names,0.62)
        if len(hits)<2: continue
        yes=_yes_entity(r['side']+' '+r['market_title'],hits); other=hits[1] if hits[0]==yes else hits[0]
        a,b=stats.get(yes,{}),stats.get(other,{})
        # Standardized lightweight team-strength features from season rates.
        def f(d,k,default=0):
            try:return float(d.get(k,default))
            except:return default
        # OPS is usually available as string; ERA lower is better.
        ops_diff=f(a,'ops',0.720)-f(b,'ops',0.720)
        era_diff=f(b,'era',4.20)-f(a,'era',4.20)
        score=0.45 + 1.6*ops_diff + 0.22*era_diff
        import math
        p=1/(1+math.exp(-score))
        q=0.78 if a and b else 0.52
        r.update(model_prob=clamp(p),data_quality=q,reason=f'Independent MLB baseline: season OPS and ERA differential; YES mapped to {yes}.')
        out.append(r)
    return out


def build_cfb_rows(rows):
    if not CFBD_API_KEY: return []
    try:
        games=CFBClient().games(date.today().year) or []
        raw=CFBClient().team_stats(date.today().year) or []
    except Exception: return []
    names=[]
    for g in games: names += [g.get('home_team',''),g.get('away_team','')]
    stats={}
    # CFBD team stats are a list of stat rows; turn them into team->metric dict.
    for row in raw:
        team=row.get('team'); stat=row.get('stat'); value=row.get('value')
        if team and stat:
            stats.setdefault(team,{})[stat]=value
    out=[]
    for r in rows:
        if r['sport']!='CFB': continue
        hits=find_two(r['market_title'],[x for x in names if x],0.62)
        if len(hits)<2: continue
        yes=_yes_entity(r['side']+' '+r['market_title'],hits); other=hits[1] if hits[0]==yes else hits[0]
        a,b=stats.get(yes,{}),stats.get(other,{})
        def num(d,keys,default=0):
            for k in keys:
                try:return float(d.get(k,default))
                except: pass
            return default
        off=num(a,['pointsPerGame','total_ppa','passingPPA'],0)-num(b,['pointsPerGame','total_ppa','passingPPA'],0)
        # Lower opponent scoring allowed is better.
        deff=num(b,['pointsPerGameAllowed','total_defense'],0)-num(a,['pointsPerGameAllowed','total_defense'],0)
        p,q=cfb_model.estimate(offense_diff=off/10,defense_diff=deff/10)
        if not a or not b: q=0.52
        r.update(model_prob=p,data_quality=q,reason=f'Independent CFB baseline for {yes} vs {other}; season team-stat fields available={bool(a and b)}.')
        out.append(r)
    return out


def build_tennis_rows(rows):
    out=[]
    cache={}
    for r in rows:
        if r['sport']!='Tennis': continue
        # Try both ATP and WTA datasets; exact names in the title are required.
        found=None
        for tour in ['ATP','WTA']:
            try:
                if tour not in cache: cache[tour]=load_matches(tour)
                df=cache[tour]
                names=pd.unique(pd.concat([df['winner_name'],df['loser_name']])).tolist()
                hits=find_two(r['market_title'],names,0.78)
                if len(hits)>=2:
                    found=(df,hits); break
            except Exception: continue
        if not found: continue
        df,hits=found; yes=_yes_entity(r['side']+' '+r['market_title'],hits); other=hits[1] if hits[0]==yes else hits[0]
        fa=recent_player_form(df,yes,10); fb=recent_player_form(df,other,10)
        if fa['win_rate'] is None or fb['win_rate'] is None: continue
        p,q=tennis_model.estimate(yes,other,fa['win_rate'],fb['win_rate'])
        r.update(model_prob=p,data_quality=q,reason=f'Independent tennis baseline: last-10 win rate from current-season match data; YES mapped to {yes}.')
        out.append(r)
    return out


def build_edge_board(min_edge=0.07,min_conf=0.58,max_markets=300):
    markets=KalshiClient().all_open_markets(max_markets)
    rows=_market_rows(markets)
    by={'MLB':[],'CFB':[],'Tennis':[]}
    for r in rows: by[r['sport']].append(r)
    combined=build_tennis_rows(by['Tennis'])+build_mlb_rows(by['MLB'])+build_cfb_rows(by['CFB'])
    # Keep discovered markets even if model couldn't produce a valid estimate: PASS is intentional.
    seen={x['ticker'] for x in combined}
    for r in rows:
        if r['ticker'] not in seen:
            r.update(model_prob=None,data_quality=0.0,reason='No independently verified matchup/stat model available. PASS.')
            combined.append(r)
    for r in combined:
        r['edge']=None if r.get('model_prob') is None else r['model_prob']-r['market_prob']
        r['verdict']=verdict(r.get('model_prob'),r['market_prob'],r.get('data_quality',0),min_edge,min_conf)
        r['rank_score']=(-1 if r['edge'] is None else r['edge']) + 0.01*float(r.get('data_quality',0))
    df=pd.DataFrame(combined)
    if df.empty: return df
    order={'STRONG':0,'WATCH':1,'PASS':2}; df['vorder']=df['verdict'].map(order).fillna(3)
    df=df.sort_values(['vorder','rank_score'],ascending=[True,False]).drop(columns=['vorder']).reset_index(drop=True)
    df.insert(0,'rank',range(1,len(df)+1))
    return df
