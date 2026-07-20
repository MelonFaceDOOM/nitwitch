"""Bot-parity read helpers for movienights browse / stats commands.

Pure ORM querysets and aggregates — ready for future templates or JSON views.
Plotting and external scrapes (ebert) are out of scope.
"""

from __future__ import annotations

from typing import List, Optional

from django.db.models import Avg, Count, Exists, OuterRef, Q, QuerySet

from .models import DiscordUser, Endorsement, Guild, Movie, Rating, Review


def _suggestions_base(guild: Guild) -> QuerySet:
    return (
        Movie.objects
        .filter(guild=guild)
        .filter(Q(watched=0) | Q(watched__isnull=True))
        .select_related('user')
    )


def _watched_base(guild: Guild) -> QuerySet:
    return (
        Movie.objects
        .filter(guild=guild, watched=1)
        .select_related('user')
    )


def suggestions(guild: Guild, user: Optional[DiscordUser] = None) -> QuerySet:
    qs = _suggestions_base(guild)
    if user is not None:
        qs = qs.filter(user=user)
    return qs.annotate(
        endorsement_count=Count('endorsements', distinct=True),
    ).order_by('-endorsement_count', '-date_suggested', 'title')


def endorsed_by(guild: Guild, user: DiscordUser) -> QuerySet:
    """Suggestions the user has endorsed."""
    return (
        _suggestions_base(guild)
        .filter(endorsements__user=user, endorsements__guild=guild)
        .annotate(endorsement_count=Count('endorsements', distinct=True))
        .order_by('-endorsement_count', '-date_suggested', 'title')
        .distinct()
    )


def endorsements_for_user(guild: Guild, user: DiscordUser) -> QuerySet:
    """Endorsement rows by this user (with movie)."""
    return (
        Endorsement.objects
        .filter(guild=guild, user=user)
        .select_related('movie', 'movie__user')
        .order_by('-date', 'id')
    )


def ratings_for_user(guild: Guild, user: DiscordUser) -> QuerySet:
    return (
        Rating.objects
        .filter(guild=guild, user=user)
        .select_related('movie', 'movie__user')
        .order_by('-rating', 'movie__title')
    )


def unrated(guild: Guild, user: DiscordUser) -> QuerySet:
    """Watched movies the user has not rated."""
    rated = Rating.objects.filter(movie_id=OuterRef('pk'), user_id=user.id)
    return (
        _watched_base(guild)
        .annotate(viewer_rated=Exists(rated))
        .filter(viewer_rated=False)
        .order_by('-date_watched', 'title')
    )


def movienights(guild: Guild, user: Optional[DiscordUser] = None) -> QuerySet:
    qs = _watched_base(guild).annotate(
        avg_rating=Avg('ratings__rating'),
        rating_count=Count('ratings', distinct=True),
    )
    if user is not None:
        qs = qs.filter(user=user)
    return qs.order_by('-date_watched', 'title')


def top_movienights(
    guild: Guild,
    user: Optional[DiscordUser] = None,
    min_ratings: int = 2,
) -> QuerySet:
    qs = (
        _watched_base(guild)
        .annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings', distinct=True),
        )
        .filter(rating_count__gte=min_ratings)
    )
    if user is not None:
        qs = qs.filter(user=user)
    return qs.order_by('-avg_rating', '-rating_count', 'title')


def top_ratings(guild: Guild, user: DiscordUser) -> QuerySet:
    return ratings_for_user(guild, user)


def random_suggestion(guild: Guild) -> Optional[Movie]:
    return _suggestions_base(guild).order_by('?').first()


def seen_count(guild: Guild) -> int:
    return _watched_base(guild).count()


def find_movies(guild: Guild, q: str) -> QuerySet:
    q = (q or '').strip()
    if not q:
        return Movie.objects.none()
    return (
        Movie.objects
        .filter(guild=guild, title__icontains=q)
        .select_related('user')
        .order_by('title')
    )


def find_users(guild: Guild, q: str) -> QuerySet:
    """Users who appear in this guild's movies / ratings / endorsements."""
    q = (q or '').strip()
    if not q:
        return DiscordUser.objects.none()
    member_ids = set(
        Movie.objects.filter(guild=guild).values_list('user_id', flat=True)
    )
    member_ids |= set(
        Rating.objects.filter(guild=guild).values_list('user_id', flat=True)
    )
    member_ids |= set(
        Endorsement.objects.filter(guild=guild).values_list('user_id', flat=True)
    )
    return (
        DiscordUser.objects
        .filter(id__in=member_ids)
        .filter(Q(username__icontains=q) | Q(global_name__icontains=q))
        .order_by('global_name', 'username', 'id')
    )


def reviews_search(guild: Guild, q: str) -> List[Review]:
    """Simple keyword filter over review text, reviewer name, and movie title."""
    q = (q or '').strip()
    qs = (
        Review.objects
        .filter(guild=guild)
        .select_related('user', 'movie')
        .order_by('-date')
    )
    if not q:
        return list(qs[:50])
    tokens = [t for t in q.lower().split() if t]
    scored = []
    for rev in qs:
        hay = ' '.join([
            rev.review_text or '',
            rev.user.display_name,
            rev.movie.title if rev.movie_id else '',
        ]).lower()
        score = sum(1 for t in tokens if t in hay)
        if score:
            scored.append((score, rev))
    scored.sort(key=lambda pair: (-pair[0], pair[1].id))
    return [rev for _, rev in scored]


def standings(guild: Guild) -> List[dict]:
    """Chooser standings: avg rating of their watched movies (min 1 rating each)."""
    rows = (
        _watched_base(guild)
        .annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings', distinct=True),
        )
        .filter(rating_count__gte=1)
        .values('user_id')
        .annotate(
            movie_count=Count('id', distinct=True),
            mean_avg=Avg('avg_rating'),
        )
        .order_by('-mean_avg', '-movie_count')
    )
    user_ids = [r['user_id'] for r in rows]
    users = {
        u.id: u
        for u in DiscordUser.objects.filter(id__in=user_ids)
    }
    out = []
    for row in rows:
        user = users.get(row['user_id'])
        out.append({
            'user': user,
            'user_id': row['user_id'],
            'movie_count': row['movie_count'],
            'mean_avg': row['mean_avg'],
            'display_name': user.display_name if user else str(row['user_id']),
        })
    return out


def attendance(guild: Guild, biggest: bool = True) -> List[dict]:
    """Watched movies ranked by rating_count (attendance proxy)."""
    qs = (
        _watched_base(guild)
        .annotate(rating_count=Count('ratings', distinct=True))
        .order_by(('-' if biggest else '') + 'rating_count', 'title')
    )
    return [
        {
            'movie': m,
            'title': m.title,
            'rating_count': m.rating_count,
            'date_watched': m.date_watched,
        }
        for m in qs[:50]
    ]
