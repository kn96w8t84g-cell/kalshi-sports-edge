import requests
from edge.config import BASE_URL, USER_AGENT

class KalshiClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.s = requests.Session()
        self.s.headers.update({'User-Agent': USER_AGENT})

    def markets(self, status='open', limit=100, cursor=None):
        p={'status':status,'limit':limit}
        if cursor: p['cursor']=cursor
        r=self.s.get(f'{self.base_url}/markets', params=p, timeout=20)
        r.raise_for_status(); return r.json()

    def all_open_markets(self, max_items=300):
        out=[]; cursor=None
        while len(out)<max_items:
            data=self.markets(limit=min(100,max_items-len(out)),cursor=cursor)
            out.extend(data.get('markets',[])); cursor=data.get('cursor')
            if not cursor: break
        return out[:max_items]

    def orderbook(self,ticker):
        r=self.s.get(f'{self.base_url}/markets/{ticker}/orderbook', timeout=20)
        r.raise_for_status(); return r.json()
