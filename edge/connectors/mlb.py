import requests
from datetime import date

BASE='https://statsapi.mlb.com/api/v1'

class MLBClient:
    def __init__(self): self.s=requests.Session()
    def schedule(self, game_date=None):
        d=game_date or date.today().isoformat()
        r=self.s.get(f'{BASE}/schedule',params={'sportId':1,'date':d,'hydrate':'team,probablePitcher,linescore'},timeout=20)
        r.raise_for_status(); return r.json()
    def team_stats(self, team_id, season=None):
        season=season or date.today().year
        r=self.s.get(f'{BASE}/teams/{team_id}/stats',params={'stats':'season','group':'hitting,pitching','season':season},timeout=20)
        r.raise_for_status(); return r.json()
