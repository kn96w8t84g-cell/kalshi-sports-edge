# 📊 Kalshi Sports Edge — iPhone-ready

Personal research dashboard for comparing independent sports probability estimates with Kalshi market prices for tennis, MLB, and college football.

**Paper/research mode only. No automatic trades. No Kalshi credentials required.**

## iPhone
See `DEPLOY_FROM_IPHONE.md` for the one-time setup. Once deployed to Streamlit Community Cloud, open the app URL in Safari and use **Share → Add to Home Screen**.

## Local computer
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data and model notes
The system intentionally avoids fabricated confidence scores. If data is missing or the estimated edge is too small, it should PASS. Use the tracker to evaluate calibration and realized performance over a large paper sample before risking money.
