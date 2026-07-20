"""Discord OAuth2 helpers for Movienights viewer verification.

Scopes: identify + guilds. Guild list is intersected with melonbot DB rows.
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

from .models import DiscordUser, Guild

AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
TOKEN_URL = "https://discord.com/api/oauth2/token"
USER_URL = "https://discord.com/api/users/@me"
USER_GUILDS_URL = "https://discord.com/api/users/@me/guilds"

SESSION_STATE_KEY = "movienight_oauth_state"
SESSION_NEXT_KEY = "movienight_oauth_next"

OAUTH_TIMEOUT = 15
OAUTH_SCOPES = "identify guilds"


class DiscordOAuthError(Exception):
    """Raised when Discord OAuth or user upsert fails in a user-visible way."""


def oauth_configured() -> bool:
    return bool(
        getattr(settings, "DISCORD_CLIENT_ID", "")
        and getattr(settings, "DISCORD_CLIENT_SECRET", "")
        and getattr(settings, "DISCORD_OAUTH_REDIRECT_URI", "")
    )


def safe_next_path(next_url: Optional[str], fallback: str) -> str:
    """Only allow relative paths under /movienights/."""
    if not next_url:
        return fallback
    next_url = next_url.strip()
    if not next_url.startswith("/movienights/"):
        return fallback
    if "//" in next_url or "\\" in next_url or ":" in next_url:
        return fallback
    return next_url


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def authorize_url(state: str) -> str:
    params = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.DISCORD_OAUTH_REDIRECT_URI,
        "scope": OAUTH_SCOPES,
        "state": state,
        "prompt": "consent",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(code: str) -> str:
    """Exchange authorization code for access token. Returns access_token."""
    data = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "client_secret": settings.DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.DISCORD_OAUTH_REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        resp = requests.post(TOKEN_URL, data=data, headers=headers, timeout=OAUTH_TIMEOUT)
    except requests.RequestException as exc:
        raise DiscordOAuthError("Could not reach Discord to exchange the code.") from exc
    if resp.status_code != 200:
        print(
            f"[discord_oauth] token exchange failed status={resp.status_code} "
            f"body={resp.text[:500]!r} redirect_uri={settings.DISCORD_OAUTH_REDIRECT_URI!r} "
            f"client_id_set={bool(settings.DISCORD_CLIENT_ID)}"
        )
        if resp.status_code == 401:
            raise DiscordOAuthError(
                "Discord rejected client credentials (check DISCORD_CLIENT_ID / "
                "DISCORD_CLIENT_SECRET in .env — not the bot token)."
            )
        raise DiscordOAuthError("Discord rejected the authorization code.")
    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise DiscordOAuthError("Discord did not return an access token.")
    return token


def fetch_discord_user(access_token: str) -> Dict[str, Any]:
    try:
        resp = requests.get(
            USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=OAUTH_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise DiscordOAuthError("Could not reach Discord for your profile.") from exc
    if resp.status_code != 200:
        raise DiscordOAuthError("Could not load your Discord profile.")
    data = resp.json()
    if "id" not in data:
        raise DiscordOAuthError("Discord profile was missing an id.")
    return data


def fetch_discord_guilds(access_token: str) -> List[Dict[str, Any]]:
    try:
        resp = requests.get(
            USER_GUILDS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=OAUTH_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise DiscordOAuthError("Could not reach Discord for your servers.") from exc
    if resp.status_code != 200:
        raise DiscordOAuthError("Could not load your Discord servers.")
    data = resp.json()
    if not isinstance(data, list):
        raise DiscordOAuthError("Discord returned an unexpected guild list.")
    return data


def _clip(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text[:max_len] if len(text) > max_len else text


def _guild_icon_url(guild_id: int, icon_hash: Optional[str]) -> Optional[str]:
    if not icon_hash:
        return None
    return f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png"


def upsert_discord_user_from_oauth(profile: Dict[str, Any]) -> Tuple[DiscordUser, Optional[str]]:
    """Upsert users row from Discord @me. Returns (user, warning_or_None)."""
    user_id = int(profile["id"])
    username = _clip(profile.get("username"), 64)
    global_name = _clip(profile.get("global_name"), 64)
    now = timezone.now()

    try:
        user, _created = DiscordUser.objects.update_or_create(
            id=user_id,
            defaults={
                "username": username,
                "global_name": global_name,
                "updated_at": now,
            },
        )
        return user, None
    except Exception:
        existing = DiscordUser.objects.filter(pk=user_id).first()
        if existing is not None:
            return existing, (
                "Connected, but could not update your name in the database "
                "(need write access on users)."
            )
        raise DiscordOAuthError(
            "Your Discord account is not in the movie database yet. "
            "Use melonbot in a server (!add / !rate) once, or grant Nitwitch "
            "INSERT/UPDATE on the users table so OAuth can create the row."
        )


def sync_guilds_from_oauth(discord_guilds: Sequence[Dict[str, Any]]) -> List[int]:
    """Upsert names for guilds already in the DB; return ids the user can browse.

    Only returns guild ids that exist in melonbot (intersection). Best-effort
    name/icon updates; membership list still works if writes fail.
    """
    oauth_by_id = {}
    for g in discord_guilds:
        try:
            gid = int(g["id"])
        except (KeyError, TypeError, ValueError):
            continue
        oauth_by_id[gid] = g

    if not oauth_by_id:
        return []

    known = list(Guild.objects.filter(id__in=list(oauth_by_id.keys())))
    now = timezone.now()
    for guild in known:
        payload = oauth_by_id.get(guild.id) or {}
        name = _clip(payload.get("name"), 128)
        icon_url = _guild_icon_url(guild.id, payload.get("icon"))
        try:
            update_fields = []
            if name and guild.name != name:
                guild.name = name
                update_fields.append("name")
            if icon_url and guild.icon_url != icon_url:
                guild.icon_url = icon_url
                update_fields.append("icon_url")
            if update_fields:
                guild.updated_at = now
                update_fields.append("updated_at")
                guild.save(update_fields=update_fields)
        except Exception:
            pass

    return [g.id for g in known]
