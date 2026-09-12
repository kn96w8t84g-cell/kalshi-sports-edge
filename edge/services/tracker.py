from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

PATH=Path('data/predictions.csv')
COLS=['saved_at','ticker','sport','market_title','side','model_prob','market_prob','edge','verdict','data_quality','reason','outcome','settled_price']

def load_predictions():
    if not PATH.exists(): return pd.DataFrame(columns=COLS)
    df=pd.read_csv(PATH)
    for c in COLS:
        if c not in df: df[c]=None
    return df[COLS]

def append_predictions(df):
    PATH.parent.mkdir(parents=True,exist_ok=True)
    x=df.copy(); x['saved_at']=datetime.now(timezone.utc).isoformat(); x['outcome']=''; x['settled_price']=''
    for c in COLS:
        if c not in x: x[c]=''
    x=x[COLS]
    old=load_predictions(); pd.concat([old,x],ignore_index=True).drop_duplicates(subset=['ticker','saved_at']).to_csv(PATH,index=False)

def performance_summary(df):
    if df.empty: return {'predictions':0,'settled':0,'win_rate':None,'brier_score':None}
    settled=df[df['outcome'].isin(['win','loss'])].copy()
    if settled.empty: return {'predictions':len(df),'settled':0,'win_rate':None,'brier_score':None}
    y=(settled['outcome']=='win').astype(float).to_numpy()
    p=pd.to_numeric(settled['model_prob'],errors='coerce').fillna(0.5).to_numpy()
    return {'predictions':len(df),'settled':len(settled),'win_rate':float(y.mean()),'brier_score':float(np.mean((p-y)**2))}
