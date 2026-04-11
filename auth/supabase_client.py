"""
supabase_client.py — Thin wrappers around Supabase Auth REST API.

WHY NOT USE supabase-py?
Because the official Python SDK is heavier than we need and adds one more
thing to learn. Supabase Auth is a simple REST API — we just POST to
endpoints with the anon key and get back JSON. Same pattern as our Airtable
helpers.

WHAT THIS MODULE DOES
Four functions that map to the auth actions we need:
  - login_user(email, password)        → logs in, returns access_token + user
  - logout_user(access_token)          → revokes the session
  - forgot_password(email)             → triggers password reset email
  - reset_password(access_token, new)  → updates password after user clicks email link

Each function returns a dict with {success: True/False, ...} so the calling
route can easily check if things worked.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def _get_config():
    """
    Read Supabase URL and anon key from environment.
    Returns (url, anon_key) tuple. Returns (None, None) on missing config.
    """
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not url or not key:
        print("ERROR: Supabase credentials missing from .env")
        print("  Need SUPABASE_URL and SUPABASE_ANON_KEY")
        return None, None

    return url, key


def _auth_headers(access_token=None):
    """
    Build the headers needed for a Supabase Auth API call.
    The anon key always goes in the "apikey" header.
    If an access_token is provided, it goes in Authorization as a Bearer token.
    """
    _, anon_key = _get_config()
    headers = {
        "apikey": anon_key,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


# ============================================================
# LOGIN
# ============================================================

def login_user(email, password):
    """
    Log a user in with email and password.

    Returns a dict like:
        {
            "success": True,
            "user_id": "bc93dd2f-...",
            "email": "user@example.com",
            "access_token": "eyJ...",
            "refresh_token": "...",
        }

    Or on failure:
        {
            "success": False,
            "error": "Invalid login credentials"
        }
    """
    url, _ = _get_config()
    if not url:
        return {"success": False, "error": "Supabase not configured"}

    endpoint = f"{url}/auth/v1/token?grant_type=password"

    try:
        resp = requests.post(
            endpoint,
            headers=_auth_headers(),
            json={"email": email, "password": password},
            timeout=10,
        )

        data = resp.json()

        if resp.status_code != 200:
            # Supabase returns an "error_description" or "msg" field on failure
            error = data.get("error_description") or data.get("msg") or "Login failed"
            return {"success": False, "error": error}

        # Success — pull out the bits we need
        return {
            "success": True,
            "user_id": data["user"]["id"],
            "email": data["user"]["email"],
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
        }

    except requests.RequestException as e:
        return {"success": False, "error": f"Could not reach Supabase: {e}"}


# ============================================================
# LOGOUT
# ============================================================

def logout_user(access_token):
    """
    Revoke the current session on Supabase's side.
    Flask should also clear its own session after calling this.
    """
    url, _ = _get_config()
    if not url or not access_token:
        return {"success": False, "error": "Missing token or config"}

    endpoint = f"{url}/auth/v1/logout"

    try:
        resp = requests.post(
            endpoint,
            headers=_auth_headers(access_token),
            timeout=10,
        )
        # Logout returns 204 (No Content) on success
        return {"success": resp.status_code in (200, 204)}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


# ============================================================
# FORGOT PASSWORD
# ============================================================

def forgot_password(email, redirect_to=None):
    """
    Trigger Supabase to send a password reset email.
    Supabase handles the email delivery and includes a magic link.

    Args:
        email: The user's email address
        redirect_to: URL to redirect to after they click the link
                     (usually http://localhost:5000/reset-password in dev)
    """
    url, _ = _get_config()
    if not url:
        return {"success": False, "error": "Supabase not configured"}

    endpoint = f"{url}/auth/v1/recover"
    payload = {"email": email}
    if redirect_to:
        payload["redirect_to"] = redirect_to

    try:
        resp = requests.post(
            endpoint,
            headers=_auth_headers(),
            json=payload,
            timeout=10,
        )

        if resp.status_code in (200, 204):
            return {"success": True}

        data = resp.json() if resp.text else {}
        error = data.get("error_description") or data.get("msg") or "Reset failed"
        return {"success": False, "error": error}

    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


# ============================================================
# RESET PASSWORD (after user clicks reset email link)
# ============================================================

def reset_password(access_token, new_password):
    """
    Update a user's password. Requires a valid access_token from the
    reset email flow.
    """
    url, _ = _get_config()
    if not url:
        return {"success": False, "error": "Supabase not configured"}

    endpoint = f"{url}/auth/v1/user"

    try:
        resp = requests.put(
            endpoint,
            headers=_auth_headers(access_token),
            json={"password": new_password},
            timeout=10,
        )

        if resp.status_code == 200:
            return {"success": True}

        data = resp.json() if resp.text else {}
        error = data.get("error_description") or data.get("msg") or "Update failed"
        return {"success": False, "error": error}

    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


# ============================================================
# GET CURRENT USER (from access token)
# ============================================================

def get_user(access_token):
    """
    Fetch the current user's info using their access token.
    Useful for verifying a session is still valid.
    """
    url, _ = _get_config()
    if not url or not access_token:
        return None

    endpoint = f"{url}/auth/v1/user"

    try:
        resp = requests.get(
            endpoint,
            headers=_auth_headers(access_token),
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None
