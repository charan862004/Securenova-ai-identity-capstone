import os
import secrets
from urllib.parse import urlencode

import jwt
import requests
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, session, url_for

load_dotenv()

DOMAIN = os.getenv("AUTH0_DOMAIN")
CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUDIENCE = os.getenv("AUTH0_AUDIENCE")
PORT = 3000

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url=f"https://{DOMAIN}/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid profile email offline_access read:ai-data write:admin",
        "code_challenge_method": "S256",  # turns PKCE on
    },
)

jwks_client = jwt.PyJWKClient(f"https://{DOMAIN}/.well-known/jwks.json")
TOKENS = {}  # demo only: tokens stay on the server, not in the cookie


def verify(token_str):
    key = jwks_client.get_signing_key_from_jwt(token_str).key
    return jwt.decode(
        token_str,
        key,
        algorithms=["RS256"],
        audience=AUDIENCE,
        issuer=f"https://{DOMAIN}/",
    )


def require_scope(scope):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, (jsonify(error="missing token"), 401)
    try:
        claims = verify(header[7:])
    except jwt.ExpiredSignatureError:
        return None, (jsonify(error="token expired"), 401)
    except jwt.PyJWTError:
        return None, (jsonify(error="invalid token"), 401)
    if scope not in claims.get("scope", "").split():
        return None, (jsonify(error=f"missing scope {scope}"), 403)
    return claims, None


@app.route("/")
def home():
    return '<a href="/login">Log in with Auth0</a>'


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True),
        audience=AUDIENCE,
    )


@app.route("/callback")
def callback():
    token = oauth.auth0.authorize_access_token()
    sid = secrets.token_hex(16)
    session["sid"] = sid
    TOKENS[sid] = {
        "access_token": token["access_token"],
        "id_token": token["id_token"],
    }
    # demo only: save the refresh token locally for the rotation test (Project 4)
    if token.get("refresh_token"):
        with open("refresh_token.txt", "w") as f:
            f.write(token["refresh_token"])
        print("Refresh token saved to refresh_token.txt (demo only)")
    return redirect("/demo")


@app.route("/api/chat")
def chat():
    claims, err = require_scope("read:ai-data")
    if err:
        return err
    return jsonify(reply="Hello from the SecureNova chat API", caller=claims["sub"])


@app.route("/api/admin")
def admin():
    claims, err = require_scope("write:admin")
    if err:
        return err
    return jsonify(message="Admin action allowed", caller=claims["sub"])


@app.route("/demo")
def demo():
    t = TOKENS.get(session.get("sid"))
    if not t:
        return redirect("/login")
    headers = {"Authorization": "Bearer " + t["access_token"]}
    base = f"http://localhost:{PORT}"
    chat_r = requests.get(base + "/api/chat", headers=headers)
    admin_r = requests.get(base + "/api/admin", headers=headers)
    return (
        "<pre>"
        f"/api/chat  -> {chat_r.status_code} {chat_r.text}\n"
        f"/api/admin -> {admin_r.status_code} {admin_r.text}\n"
        "</pre>"
        '<a href="/tokens">Show tokens</a> | <a href="/logout">Log out</a>'
    )


@app.route("/tokens")
def tokens():
    # demo only: lets you copy the tokens into jwt.io
    t = TOKENS.get(session.get("sid"))
    if not t:
        return redirect("/login")
    return (
        "<h3>Access token</h3><pre style='white-space:pre-wrap'>" + t["access_token"] + "</pre>"
        "<h3>ID token</h3><pre style='white-space:pre-wrap'>" + t["id_token"] + "</pre>"
    )


@app.route("/logout")
def logout():
    TOKENS.pop(session.get("sid"), None)
    session.clear()
    query = urlencode({"returnTo": f"http://localhost:{PORT}", "client_id": CLIENT_ID})
    return redirect(f"https://{DOMAIN}/v2/logout?{query}")


app.run(port=PORT)