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
if st.button("🏟️ Check Kalshi sports feed"):
    from edge.connectors.kalshi import KalshiClient
    from edge.services.kalshi_parser import classify_market

    try:
        client = KalshiClient()

        raw_data = client.markets(
            status="open",
            limit=100,
        )

        raw_markets = raw_data.get("markets", [])

        def is_combo(m):
            normalized = {
                str(k).strip().lower().replace(" ", "_"): v
                for k, v in m.items()
            }

            ticker = str(
                normalized.get("ticker") or ""
            ).upper()

            event_ticker = str(
                normalized.get("event_ticker") or ""
            ).upper()

            multi = str(
                normalized.get("multivariate_event_ticker") or ""
            ).upper()

            collection = str(
                normalized.get("mve_collection_ticker") or ""
            ).upper()

            legs = normalized.get("mve_selected_legs")

            text = " ".join([
                ticker,
                event_ticker,
                multi,
                collection,
            ])

            return (
                "CROSSCATEGORY" in text
                or "SHARD" in text
                or bool(legs)
            )

        combo_count = sum(
            1 for m in raw_markets
            if is_combo(m)
        )

        normal_count = len(raw_markets) - combo_count

        usable = client.all_open_markets(
            max_items=100,
            max_pages=10,
        )

        tennis = sum(
            1 for m in usable
            if classify_market(m) == "Tennis"
        )

        mlb = sum(
            1 for m in usable
            if classify_market(m) == "MLB"
        )

        cfb = sum(
            1 for m in usable
            if classify_market(m) == "CFB"
        )

        st.success("Kalshi connection is working ✅")

        st.write("### Feed status")
        st.write(f"Raw markets checked: **{len(raw_markets)}**")
        st.write(f"Combo markets rejected: **{combo_count}**")
        st.write(f"Normal markets on first page: **{normal_count}**")
        st.write(f"Usable priced markets found: **{len(usable)}**")

        st.write("### Sports found")
        st.write(f"🎾 Tennis: **{tennis}**")
        st.write(f"⚾ MLB: **{mlb}**")
        st.write(f"🏈 College Football: **{cfb}**")

    except Exception as e:
        st.error(f"Feed check failed: {e}")
    
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