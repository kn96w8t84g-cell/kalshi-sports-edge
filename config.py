import os
BASE_URL = os.getenv('KALSHI_BASE_URL','https://external-api.kalshi.com/trade-api/v2')
CFBD_API_KEY = os.getenv('CFBD_API_KEY','')
USER_AGENT = os.getenv('USER_AGENT','KalshiSportsEdge/3.0 personal-research')
MIN_EDGE = float(os.getenv('MIN_EDGE','0.07'))
MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE','0.58'))
MAX_MARKETS = int(os.getenv('MAX_MARKETS','300'))
