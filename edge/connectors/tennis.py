import io, requests, pandas as pd

# Historical ATP/WTA match data. Network fetch is lazy so the dashboard still works without it.
URLS={
 'ATP':'https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2026.csv',
 'WTA':'https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_2026.csv'
}

def load_matches(tour):
    url=URLS[tour]
    r=requests.get(url,timeout=30); r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content))

def recent_player_form(df, player, n=10):
    rows=df[(df.winner_name==player)|(df.loser_name==player)].copy().sort_values('tourney_date',ascending=False).head(n)
    if rows.empty: return {'matches':0,'wins':0,'losses':0,'win_rate':None}
    wins=int((rows.winner_name==player).sum()); return {'matches':len(rows),'wins':wins,'losses':len(rows)-wins,'win_rate':wins/len(rows)}
