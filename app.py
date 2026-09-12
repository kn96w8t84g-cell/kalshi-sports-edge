import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from edge.services.pipeline import build_edge_board
from edge.services.tracker import load_predictions, performance_summary, append_predictions

load_dotenv()
st.set_page_config(page_title='Kalshi Sports Edge', page_icon='📊', layout='wide')

st.title('📊 Kalshi Sports Edge')
st.write("DEBUG BUILD: NEW CODE ACTIVE")
st.caption('Independent sports probability research vs. Kalshi prices — paper/research mode only.')
try:
    
with st.sidebar:
    st.header('Controls')
    min_edge = st.slider('Minimum edge', 0.00, 0.25, float(os.getenv('MIN_EDGE', '0.07')), 0.01)
    min_conf = st.slider('Minimum model probability', 0.50, 0.90, float(os.getenv('MIN_CONFIDENCE', '0.58')), 0.01)
    max_markets = st.slider('Markets to scan', 50, 500, int(os.getenv('MAX_MARKETS', '300')), 50)
    refresh = st.button('🔄 Scan Kalshi now', type='primary')
    st.divider()
    st.warning('This tool does not guarantee wins. Treat every result as a hypothesis and paper-test it.')

if refresh or 'board' not in st.session_state:
    with st.spinner('Scanning Kalshi and building model estimates...'):
        try:
            board = build_edge_board(min_edge=min_edge, min_conf=min_conf, max_markets=max_markets)
            st.session_state.board = board
        except Exception as e:
            st.error(f'Scan failed: {e}')
            board = pd.DataFrame()
else:
    board = st.session_state.board

if not board.empty:
    picks = board[board['verdict'].isin(['STRONG', 'WATCH'])].copy()
    picks['model_pct'] = (picks['model_prob'] * 100).round(1)
    picks['kalshi_pct'] = (picks['market_prob'] * 100).round(1)
    picks['edge_pct'] = (picks['edge'] * 100).round(1)
    st.subheader('🔥 Top edges')
    cols = ['rank','sport','market_title','side','model_pct','kalshi_pct','edge_pct','verdict','data_quality','reason']
    st.dataframe(picks[cols].head(20), use_container_width=True, hide_index=True)

    st.subheader('All scanned markets')
    st.dataframe(board, use_container_width=True, hide_index=True)

    if st.button('💾 Save these predictions to tracker'):
        append_predictions(picks)
        st.success(f'Saved {len(picks)} predictions.')
else:
    st.info('No usable markets were returned. Try Scan again or check the data-source status below.')

with st.expander('📈 Tracker'):
    hist = load_predictions()
    st.write(performance_summary(hist))
    if not hist.empty:
        st.dataframe(hist.tail(100), use_container_width=True, hide_index=True)

with st.expander('ℹ️ How the edge is calculated'):
    st.markdown('''
**Model probability** is estimated independently from the Kalshi quote using sports features.

**Edge = model probability − executable market price.**

A pick only reaches **STRONG** when the edge clears the configured threshold and the model/data quality are sufficient. Otherwise the system says **WATCH** or **PASS**.

The tracker scores predictions with win rate and Brier score. Brier score is especially useful because it evaluates probability quality, not just whether the final pick won.
''')