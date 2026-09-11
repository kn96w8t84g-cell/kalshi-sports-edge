# Kalshi Sports Edge — iPhone setup

The easiest way to use this app on iPhone is to deploy it once to Streamlit Community Cloud. After that, you use it like a normal website and can add it to your iPhone Home Screen.

## 1. Create a GitHub account
Go to https://github.com/ and create/sign into an account.

## 2. Create a repository
Create a new repository named `kalshi-sports-edge`.
For the easiest setup, make it **Public** and do not add extra files beyond the repository defaults.

## 3. Upload this folder
Download the ZIP from ChatGPT, unzip it in the iPhone Files app, then in GitHub open your new repository → **Add file → Upload files** and upload the files/folders inside `Kalshi_Sports_Edge_iPhone`.

Important: upload the contents of the folder so that `app.py` and `requirements.txt` are at the repository root. Do not upload the ZIP as the only file.

## 4. Deploy
Open https://share.streamlit.io/ and sign in.
Choose **Create app** → **Yup, I have an app**.
Select your GitHub repository, branch `main`, and entrypoint `app.py`.
Choose a custom app subdomain if you want one, such as `yourname-kalshi-edge` if available.
Click **Deploy**.

## 5. Add it to your iPhone Home Screen
Open the resulting `*.streamlit.app` URL in Safari.
Tap the Share button → **Add to Home Screen** → Add.

Now you can launch Kalshi Sports Edge from your iPhone like an app.

## Optional CFB key
The app can run without a CollegeFootballData key, but adding one gives the CFB connector more data. Never put a Kalshi private key, password, seed phrase, or trading credential in GitHub.
