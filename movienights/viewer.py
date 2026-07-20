"""Pre-auth viewer identity for personal Movienights filters.

Stores a Discord snowflake (+ guild membership ids from OAuth) in the session
after Discord OAuth (identify + guilds). Not a Nitwitch site login.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from django.http import HttpRequest

from .models import DiscordUser

SESSION_KEY = 'movienight_viewer_id'
GUILD_IDS_SESSION_KEY = 'movienight_viewer_guild_ids'
COOKIE_NAME = 'movienight_viewer_id'
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


def get_viewer(request: HttpRequest) -> Optional[DiscordUser]:
    raw = request.session.get(SESSION_KEY)
    if raw is None:
        raw = request.COOKIES.get(COOKIE_NAME)
        if raw is not None:
            try:
                request.session[SESSION_KEY] = int(raw)
                raw = request.session[SESSION_KEY]
            except (TypeError, ValueError):
                return None
    if raw is None:
        return None
    try:
        return DiscordUser.objects.filter(pk=int(raw)).first()
    except (TypeError, ValueError):
        return None


def set_viewer(request: HttpRequest, user: DiscordUser) -> None:
    request.session[SESSION_KEY] = int(user.id)


def set_viewer_guild_ids(request: HttpRequest, guild_ids: Sequence[int]) -> None:
    request.session[GUILD_IDS_SESSION_KEY] = [int(g) for g in guild_ids]


def get_viewer_guild_ids(request: HttpRequest) -> List[int]:
    raw = request.session.get(GUILD_IDS_SESSION_KEY) or []
    out = []
    for item in raw:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def viewer_can_access_guild(request: HttpRequest, guild_id: int) -> bool:
    if get_viewer(request) is None:
        return False
    return int(guild_id) in get_viewer_guild_ids(request)


def clear_viewer(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY, None)
    request.session.pop(GUILD_IDS_SESSION_KEY, None)
