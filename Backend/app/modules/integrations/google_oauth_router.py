"""
Google OAuth 2.0 Router for Multi-Tenant Calendar Integration.
Each tenant connects their own Google Calendar via OAuth.
Refresh tokens are encrypted (Fernet/AES) before storage.
"""

import os
import json
import hashlib
import base64
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from cryptography.fernet import Fernet

from app.infrastructure.database.supabase_client import SupabasePooler
from app.infrastructure.telemetry.logger_service import logger

router = APIRouter(prefix="/api/google", tags=["google-oauth"])

# --- Encryption helpers ---
def _get_fernet() -> Fernet:
    """Derive a Fernet key from SUPABASE_SERVICE_ROLE_KEY (stable secret)."""
    secret = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "fallback-secret-key")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)

def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()

# --- OAuth flow ---
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

def _get_google_client_config():
    """Read OAuth client credentials from env or credentials file."""
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

    if client_id and client_secret:
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/google/callback")]
            }
        }
    
    # Fallback: try credentials file
    creds_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "credentials", "oauth_client.json")
    if os.path.exists(creds_path):
        with open(creds_path, "r") as f:
            return json.load(f)
    
    raise HTTPException(status_code=500, detail="Google OAuth not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET.")


@router.get("/auth")
async def google_auth(tenant_id: str):
    """
    Step 1: Redirect tenant admin to Google consent screen.
    ?tenant_id=<uuid> is required.
    """
    if not tenant_id:
        raise HTTPException(400, "tenant_id is required")

    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/google/callback")
    client_config = _get_google_client_config()

    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=tenant_id,  # Pass tenant_id through state param
    )

    logger.info(f"🔑 [OAUTH] Tenant {tenant_id} → redirecting to Google consent")
    return RedirectResponse(auth_url)


@router.get("/callback")
async def google_callback(code: str, state: str):
    """
    Step 2: Google redirects back with authorization code.
    Exchange for tokens, encrypt refresh_token, store in Supabase.
    """
    tenant_id = state
    if not tenant_id:
        raise HTTPException(400, "Missing tenant state")

    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/google/callback")
    client_config = _get_google_client_config()

    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    flow.fetch_token(code=code)

    credentials = flow.credentials
    if not credentials.refresh_token:
        raise HTTPException(400, "No refresh token received. User may need to re-authorize with prompt=consent.")

    # Get user email from ID token
    from google.oauth2 import id_token as gid_token
    from google.auth.transport import requests as google_requests
    try:
        id_info = gid_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            credentials.client_id,
        )
        email = id_info.get("email", "unknown")
    except Exception:
        email = "unknown"

    # Encrypt and store
    encrypted_refresh = encrypt_token(credentials.refresh_token)
    db = SupabasePooler.get_client()
    db.table("tenants").update({
        "google_refresh_token_encrypted": encrypted_refresh,
        "google_calendar_email": email,
        "google_calendar_connected_at": "now()",
        "google_calendar_status": "connected",
    }).eq("id", tenant_id).execute()

    logger.info(f"✅ [OAUTH] Tenant {tenant_id} connected Google Calendar ({email})")

    # Redirect to frontend settings page
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/config?google=connected")


@router.post("/disconnect")
async def google_disconnect(tenant_id: str):
    """Revoke Google Calendar connection for a tenant."""
    db = SupabasePooler.get_client()
    db.table("tenants").update({
        "google_refresh_token_encrypted": None,
        "google_calendar_email": None,
        "google_calendar_connected_at": None,
        "google_calendar_status": "disconnected",
    }).eq("id", tenant_id).execute()

    logger.info(f"🔌 [OAUTH] Tenant {tenant_id} disconnected Google Calendar")
    return {"status": "disconnected"}
