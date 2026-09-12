import requests
from edge.config import CFBD_API_KEY

class CFBClient:
    def __init__(self,key=CFBD_API_KEY): self.key=key; self.base='https://api.collegefootballdata.com'
    def _get(self,path,params=None):
        if not self.key: return None
        r=requests.get(self.base+path,params=params,headers={'Authorization':f'Bearer {self.key}'},timeout=20)
        r.raise_for_status(); return r.json()
    def games(self,year): return self._get('/games',{'year':year,'seasonType':'regular'})
    def team_stats(self,year): return self._get('/stats/team',{'year':year})
    def ratings(self,year): return self._get('/ratings/sp',{'year':year})
