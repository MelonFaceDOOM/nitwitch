"""Bot-parity write actions for the movienights domain.

Rules and user-facing strings mirror melonbot Core commands. Callers (views)
supply a verified DiscordUser + guild; these functions do validation + ORM writes
and return a Result with a stable code for redirects / future UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from django.http import HttpRequest
from django.utils import timezone

from .models import DiscordUser, Endorsement, Guild, Movie, Rating, Review
from .viewer import get_viewer, viewer_can_access_guild

REVIEW_MAX_LEN = 1200


class Code(str, Enum):
    OK = 'ok'
    NEED_VIEWER = 'need_viewer'
    NEED_ACCESS = 'need_access'
    MOVIE_NOT_FOUND = 'movie_not_found'
    ALREADY_RATED = 'already_rated'
    ALREADY_WATCHED = 'already_watched'
    CANT_REMOVE_WATCHED = 'cant_remove_watched'
    CANT_ENDORSE_OWN = 'cant_endorse_own'
    ALREADY_ENDORSED = 'already_endorsed'
    NOT_ENDORSED = 'not_endorsed'
    CANT_ENDORSE_WATCHED = 'cant_endorse_watched'
    NEED_RATING = 'need_rating'
    NOT_RATED = 'not_rated'
    RATING_INVALID = 'rating_invalid'
    RATING_RANGE = 'rating_range'
    REVIEW_EMPTY = 'review_empty'
    REVIEW_TOO_LONG = 'review_too_long'
    REVIEW_UNWATCHED = 'review_unwatched'
    USER_NOT_FOUND = 'user_not_found'
    ALREADY_OWNED = 'already_owned'
    BAD_DATE = 'bad_date'
    TITLE_EMPTY = 'title_empty'
    TITLE_TAKEN = 'title_taken'
    RETURNED_TO_SUGGESTIONS = 'returned_to_suggestions'
    DB_ERROR = 'db_error'
    BAD_STATE = 'bad_state'


@dataclass
class Result:
    code: Code
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.code in (Code.OK, Code.RETURNED_TO_SUGGESTIONS)


def _msg(template: str, **kwargs) -> str:
    return template.format(**kwargs)


# Bot-parity strings (adapted from melonbot/bot.py).
MESSAGES = {
    Code.NEED_VIEWER: 'Verify with Discord first.',
    Code.NEED_ACCESS: 'You do not have access to this server.',
    Code.MOVIE_NOT_FOUND: "'{title}' doesn't exist.",
    Code.ALREADY_RATED: "'{title}' has already been rated.",
    Code.ALREADY_WATCHED: "'{title}' has already been watched or rated and can't be removed.",
    Code.CANT_REMOVE_WATCHED: "'{title}' has already been watched or rated and can't be removed.",
    Code.CANT_ENDORSE_OWN: 'You cannot endorse your own movie',
    Code.ALREADY_ENDORSED: "You have already endorsed '{title}'",
    Code.NOT_ENDORSED: "You have not endorsed '{title}'",
    Code.CANT_ENDORSE_WATCHED: "'{title}' has already been watched or rated, so it can't be endorsed.",
    Code.NEED_RATING: "you must rate '{title}' before you can review it",
    Code.NOT_RATED: "You have not yet rated '{title}'.",
    Code.RATING_INVALID: 'rating must be between 1 and 10',
    Code.RATING_RANGE: 'rating must be between 1 and 10',
    Code.REVIEW_EMPTY: "Review text can't be empty.",
    Code.REVIEW_TOO_LONG: 'Review is too long (1200 character max).',
    Code.REVIEW_UNWATCHED: "'{title}' has not been watched yet.",
    Code.USER_NOT_FOUND: "User '{name}' not found",
    Code.ALREADY_OWNED: '{title} is already owned by {username}',
    Code.BAD_DATE: (
        "Couldn't parse date {date}.\n use the format yyyy-mm-dd, i.e. 2024-12-31"
    ),
    Code.TITLE_EMPTY: 'Movie title is required.',
    Code.TITLE_TAKEN: "A movie named '{title}' already exists.",
    Code.DB_ERROR: 'Ruh roh database error',
    Code.BAD_STATE: 'a terrible thing has happened here.',
    Code.OK: 'ok',
    Code.RETURNED_TO_SUGGESTIONS: (
        "You have removed the last rating from '{title}' and so it has been "
        "returned to suggestions."
    ),
}


def require_member(
    request: HttpRequest, guild_id: int,
) -> Tuple[Optional[DiscordUser], Optional[Result]]:
    """Return (viewer, None) on success, or (None, Result) on auth failure."""
    viewer = get_viewer(request)
    if viewer is None:
        return None, Result(Code.NEED_VIEWER, MESSAGES[Code.NEED_VIEWER])
    if not viewer_can_access_guild(request, guild_id):
        return None, Result(Code.NEED_ACCESS, MESSAGES[Code.NEED_ACCESS])
    return viewer, None


def _now():
    return timezone.now()


def _find_movie(guild: Guild, title: str) -> Optional[Movie]:
    title = (title or '').strip()
    if not title:
        return None
    return (
        Movie.objects
        .filter(guild=guild, title__iexact=title)
        .select_related('user')
        .first()
    )


def _find_movie_by_id(guild: Guild, movie_id: int) -> Optional[Movie]:
    return (
        Movie.objects
        .filter(guild=guild, pk=movie_id)
        .select_related('user')
        .first()
    )


def _parse_rating(raw: str) -> Tuple[Optional[float], Optional[Result]]:
    value = (raw or '').strip()
    cutoff = value.find('/10')
    if cutoff > -1:
        value = value[:cutoff]
    try:
        rating = float(value)
        rating = int(round(rating * 100)) / 100
    except (TypeError, ValueError):
        return None, Result(Code.RATING_INVALID, MESSAGES[Code.RATING_INVALID])
    if rating < 1 or rating > 10:
        return None, Result(Code.RATING_RANGE, MESSAGES[Code.RATING_RANGE])
    return rating, None


def endorse(guild: Guild, movie: Movie, user: DiscordUser) -> Result:
    """Endorse a suggestion. Shared by suggest(auto) and the endorse action."""
    title = movie.title
    if movie.is_watched:
        return Result(
            Code.CANT_ENDORSE_WATCHED,
            _msg(MESSAGES[Code.CANT_ENDORSE_WATCHED], title=title),
        )
    if movie.user_id == user.id:
        return Result(Code.CANT_ENDORSE_OWN, MESSAGES[Code.CANT_ENDORSE_OWN])
    if Endorsement.objects.filter(guild=guild, movie=movie, user=user).exists():
        return Result(
            Code.ALREADY_ENDORSED,
            _msg(MESSAGES[Code.ALREADY_ENDORSED], title=title),
        )
    try:
        Endorsement.objects.create(
            guild=guild,
            movie=movie,
            user=user,
            date=_now(),
        )
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f"You have endorsed '{title}'.",
        data={'movie_id': movie.id, 'title': title},
    )


def suggest(guild: Guild, user: DiscordUser, title: str) -> Result:
    """Add a suggestion, or auto-endorse if it already exists as a suggestion."""
    title = (title or '').strip()
    if not title:
        return Result(Code.TITLE_EMPTY, MESSAGES[Code.TITLE_EMPTY])
    if len(title) > 256:
        title = title[:256]

    existing = _find_movie(guild, title)
    if existing is not None:
        if existing.is_watched:
            return Result(
                Code.ALREADY_RATED,
                _msg(MESSAGES[Code.ALREADY_RATED], title=existing.title),
            )
        if existing.watched in (0, None):
            return endorse(guild, existing, user)
        return Result(Code.BAD_STATE, MESSAGES[Code.BAD_STATE])

    try:
        movie = Movie.objects.create(
            guild=guild,
            title=title,
            user=user,
            watched=0,
            date_suggested=_now(),
        )
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f"'{title}' has been added.",
        data={'movie_id': movie.id, 'title': title},
    )


def remove_suggestion(guild: Guild, title: str = '', movie_id: Optional[int] = None) -> Result:
    """Remove a suggestion (watched=0 only)."""
    if movie_id is not None:
        movie = _find_movie_by_id(guild, movie_id)
        lookup = str(movie_id)
    else:
        title = (title or '').strip()
        movie = _find_movie(guild, title)
        lookup = title

    if movie is None:
        return Result(
            Code.MOVIE_NOT_FOUND,
            _msg(MESSAGES[Code.MOVIE_NOT_FOUND], title=lookup or 'movie'),
        )
    if movie.is_watched:
        return Result(
            Code.CANT_REMOVE_WATCHED,
            _msg(MESSAGES[Code.CANT_REMOVE_WATCHED], title=movie.title),
        )
    try:
        deleted, _ = Movie.objects.filter(
            pk=movie.id, guild=guild, watched=0,
        ).delete()
        if not deleted:
            return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f"'{movie.title}' has been deleted.",
        data={'title': movie.title},
    )


def unendorse(guild: Guild, movie: Movie, user: DiscordUser) -> Result:
    title = movie.title
    try:
        deleted, _ = Endorsement.objects.filter(
            guild=guild, movie=movie, user=user,
        ).delete()
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    if not deleted:
        return Result(
            Code.NOT_ENDORSED,
            _msg(MESSAGES[Code.NOT_ENDORSED], title=title),
        )
    return Result(
        Code.OK,
        f"You have unendorsed '{title}'.",
        data={'movie_id': movie.id, 'title': title},
    )


def rate(
    guild: Guild,
    movie: Movie,
    user: DiscordUser,
    raw_rating: str,
) -> Result:
    """Upsert rating and promote movie to watched (bot parity)."""
    rating, err = _parse_rating(raw_rating)
    if err is not None:
        return err
    assert rating is not None
    title = movie.title
    now = _now()
    try:
        if not movie.is_watched:
            movie.watched = 1
            fields = ['watched']
            if movie.date_watched is None:
                movie.date_watched = now
                fields.append('date_watched')
            movie.save(update_fields=fields)
        elif movie.date_watched is None:
            movie.date_watched = now
            movie.save(update_fields=['date_watched'])

        existing = Rating.objects.filter(
            guild=guild, movie=movie, user=user,
        ).first()
        if existing is not None:
            existing.rating = rating
            existing.save(update_fields=['rating'])
        else:
            Rating.objects.create(
                guild=guild,
                movie=movie,
                user=user,
                rating=rating,
                date=now,
            )
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f"You rated '{title}' {rating}/10.",
        data={'movie_id': movie.id, 'title': title, 'rating': rating},
    )


def unrate(guild: Guild, movie: Movie, user: DiscordUser) -> Result:
    title = movie.title
    try:
        deleted, _ = Rating.objects.filter(
            guild=guild, movie=movie, user=user,
        ).delete()
        if not deleted:
            return Result(
                Code.NOT_RATED,
                _msg(MESSAGES[Code.NOT_RATED], title=title),
            )
        Review.objects.filter(guild=guild, movie=movie, user=user).delete()
        if not Rating.objects.filter(movie=movie).exists():
            movie.watched = 0
            movie.date_watched = None
            movie.save(update_fields=['watched', 'date_watched'])
            return Result(
                Code.RETURNED_TO_SUGGESTIONS,
                _msg(MESSAGES[Code.RETURNED_TO_SUGGESTIONS], title=title),
                data={
                    'movie_id': movie.id,
                    'title': title,
                    'returned_to_suggestions': True,
                },
            )
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f"You have removed your rating from '{title}'.",
        data={'movie_id': movie.id, 'title': title, 'returned_to_suggestions': False},
    )


def review(guild: Guild, movie: Movie, user: DiscordUser, text: str) -> Result:
    title = movie.title
    if not movie.is_watched:
        return Result(
            Code.REVIEW_UNWATCHED,
            _msg(MESSAGES[Code.REVIEW_UNWATCHED], title=title),
        )
    if not Rating.objects.filter(movie=movie, user=user).exists():
        return Result(
            Code.NEED_RATING,
            _msg(MESSAGES[Code.NEED_RATING], title=title),
        )
    text = (text or '').strip()
    if not text:
        return Result(Code.REVIEW_EMPTY, MESSAGES[Code.REVIEW_EMPTY])
    if len(text) > REVIEW_MAX_LEN:
        return Result(Code.REVIEW_TOO_LONG, MESSAGES[Code.REVIEW_TOO_LONG])
    try:
        existing = Review.objects.filter(
            guild=guild, movie=movie, user=user,
        ).first()
        if existing is not None:
            existing.review_text = text
            existing.save(update_fields=['review_text'])
        else:
            Review.objects.create(
                guild=guild,
                movie=movie,
                user=user,
                review_text=text,
                date=_now(),
            )
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f'You have reviewed {title}.',
        data={'movie_id': movie.id, 'title': title},
    )


def transfer(
    guild: Guild,
    movie: Movie,
    target_user_id: int,
) -> Result:
    """Change movie chooser (owner) to target Discord user id."""
    title = movie.title
    try:
        target = DiscordUser.objects.filter(pk=int(target_user_id)).first()
    except (TypeError, ValueError):
        target = None
    if target is None:
        return Result(
            Code.USER_NOT_FOUND,
            _msg(MESSAGES[Code.USER_NOT_FOUND], name=str(target_user_id)),
        )
    if movie.user_id == target.id:
        return Result(
            Code.ALREADY_OWNED,
            _msg(
                MESSAGES[Code.ALREADY_OWNED],
                title=title,
                username=target.display_name,
            ),
        )
    try:
        movie.user = target
        movie.save(update_fields=['user'])
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f"'{title}' choosership has been transfered to '{target.display_name}'.",
        data={'movie_id': movie.id, 'title': title, 'user_id': target.id},
    )


def change_date_watched(guild: Guild, movie: Movie, date_str: str) -> Result:
    """Set movies.date_watched from YYYY-MM-DD."""
    raw = (date_str or '').strip()
    try:
        parsed = datetime.strptime(raw, '%Y-%m-%d')
        if timezone.is_aware(timezone.now()):
            aware = timezone.make_aware(parsed, timezone.get_current_timezone())
        else:
            aware = parsed
    except (TypeError, ValueError):
        return Result(
            Code.BAD_DATE,
            _msg(MESSAGES[Code.BAD_DATE], date=raw or '(empty)'),
        )
    try:
        movie.date_watched = aware
        movie.save(update_fields=['date_watched'])
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f'date watched of {movie.title} has been changed to {raw}.',
        data={'movie_id': movie.id, 'title': movie.title, 'date_watched': raw},
    )


def rename(guild: Guild, movie: Movie, new_title: str) -> Result:
    """Change a movie's title within its guild."""
    title = (new_title or '').strip()
    if not title:
        return Result(Code.TITLE_EMPTY, MESSAGES[Code.TITLE_EMPTY])
    if len(title) > 256:
        title = title[:256]
    if title.casefold() == (movie.title or '').casefold():
        return Result(
            Code.OK,
            f"'{movie.title}' is unchanged.",
            data={'movie_id': movie.id, 'title': movie.title},
        )
    existing = _find_movie(guild, title)
    if existing is not None and existing.id != movie.id:
        return Result(
            Code.TITLE_TAKEN,
            _msg(MESSAGES[Code.TITLE_TAKEN], title=existing.title),
        )
    try:
        movie.title = title
        movie.save(update_fields=['title'])
    except Exception:
        return Result(Code.DB_ERROR, MESSAGES[Code.DB_ERROR])
    return Result(
        Code.OK,
        f"Renamed to '{title}'.",
        data={'movie_id': movie.id, 'title': title},
    )
