import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube",
]

CLIENT_SECRET = os.path.join(os.path.dirname(__file__), "client_secret.json")
TOKEN_FILE    = os.path.join(os.path.dirname(__file__), "token.pickle")


def get_youtube():
    """Return an authenticated YouTube service. Opens browser on first run."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            auth_url, _ = flow.authorization_url(prompt="consent")
            print("\n" + "="*60)
            print(" 🔐 AUTHENTIFICATION YOUTUBE REQUISE")
            print("="*60)
            print("\n 1. Ouvre ce lien dans ton navigateur :\n")
            print(f"    {auth_url}\n")
            print(" 2. Connecte-toi avec ton compte Google YouTube")
            print(" 3. Accepte les permissions")
            print(" 4. Copie le code affiché et colle-le ici\n")
            print("="*60)
            code = input(" Code d'autorisation : ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        print("✅ Authentification réussie — token sauvegardé.")

    return build("youtube", "v3", credentials=creds)
