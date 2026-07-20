from django.db.models import Avg, Count, Exists, OuterRef, Q
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from . import actions, queries
from .actions import MESSAGES, Code, Result
from .discord_oauth import (
    SESSION_NEXT_KEY,
    SESSION_STATE_KEY,
    DiscordOAuthError,
    authorize_url,
    exchange_code,
    fetch_discord_guilds,
    fetch_discord_user,
    new_oauth_state,
    oauth_configured,
    safe_next_path,
    sync_guilds_from_oauth,
    upsert_discord_user_from_oauth,
)
from .models import DiscordUser, Endorsement, Guild, Movie, Rating, Review
from .viewer import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    GUILD_IDS_SESSION_KEY,
    clear_viewer,
    get_viewer,
    get_viewer_guild_ids,
    set_viewer,
    set_viewer_guild_ids,
    viewer_can_access_guild,
)

VIEW_LABELS = {
    'top': 'Past Movienights',
    'unwatched': 'Suggestions',
}

# sort key -> ORM field; first click is desc, second is asc
VIEW_SORTS = {
    'top': {
        'default': ('date', 'desc'),
        'fields': {
            'rating': 'avg_rating',
            'count': 'rating_count',
            'date': 'date_watched',
        },
    },
    'unwatched': {
        'default': ('date', 'desc'),
        'fields': {
            'endorsements': 'endorsement_count',
            'date': 'date_suggested',
        },
    },
}

OAUTH_ERROR_MESSAGES = {
    'denied': 'Discord authorization was cancelled.',
    'bad_state': 'OAuth session expired or was invalid. Try Verify with Discord again.',
    'bad_credentials': (
        'Discord rejected the app credentials. Set DISCORD_CLIENT_ID and '
        'DISCORD_CLIENT_SECRET in .env (Application ID + OAuth2 Client Secret '
        'from the Discord portal — not the bot token), then restart Django.'
    ),
    'no_user_row': (
        'Your Discord account is not in the movie database yet. Use melonbot '
        'once in a server, or grant Nitwitch write access on users so OAuth '
        'can create the row.'
    ),
    'oauth_failed': 'Discord verification failed. Try again.',
    'missing_code': 'Discord verification failed. Try again.',
    'not_configured': 'Discord OAuth is not configured on this server.',
}

# Success copy for *_saved / *_removed query flags (Result.message is not in the URL).
FLASH_SAVED_MESSAGES = {
    'suggest': 'Movie suggested.',
    'remove': 'Suggestion removed.',
    'endorse': 'Endorsement saved.',
    'unendorse': 'Endorsement removed.',
    'transfer': 'Chooser updated.',
    'date': 'Date watched updated.',
    'rename': 'Title updated.',
    'rating': 'Rating saved.',
    'review': 'Review saved.',
}

FLASH_REMOVED_MESSAGES = {
    'rating': 'Rating removed.',
}

# Legacy short error keys still emitted by movie_rate / movie_review redirects.
FLASH_ERROR_ALIASES = {
    'invalid': Code.RATING_INVALID,
    'range': Code.RATING_RANGE,
    'save_failed': Code.DB_ERROR,
    'missing': Code.NOT_RATED,
    'need_viewer': Code.NEED_VIEWER,
    'empty': Code.REVIEW_EMPTY,
    'too_long': Code.REVIEW_TOO_LONG,
    'need_rating': Code.NEED_RATING,
    'unwatched': Code.REVIEW_UNWATCHED,
}


def _flash_error_message(raw: str, title: str = 'this movie') -> str:
    """Map an *_error query value to a user-facing string."""
    key = (raw or '').strip()
    if not key:
        return 'Something went wrong.'
    code = FLASH_ERROR_ALIASES.get(key)
    if code is None:
        try:
            code = Code(key)
        except ValueError:
            return f'Something went wrong ({key}).'
    tmpl = MESSAGES.get(code, key)
    try:
        return tmpl.format(
            title=title,
            name='user',
            username='user',
            date='(empty)',
        )
    except (KeyError, ValueError):
        return tmpl


def _flash_context(request, prefixes, *, title: str = 'this movie'):
    """Build flash banners from *_saved / *_removed / *_error query keys."""
    flashes = []
    for prefix in prefixes:
        if request.GET.get(f'{prefix}_saved') == '1':
            flashes.append({
                'level': 'ok',
                'message': FLASH_SAVED_MESSAGES.get(prefix, 'Saved.'),
            })
        if request.GET.get(f'{prefix}_removed') == '1':
            flashes.append({
                'level': 'ok',
                'message': FLASH_REMOVED_MESSAGES.get(prefix, 'Removed.'),
            })
        err = request.GET.get(f'{prefix}_error', '')
        if err:
            flashes.append({
                'level': 'err',
                'message': _flash_error_message(err, title=title),
            })
    return {'flashes': flashes}


def _annotate_movies(qs):
    return qs.annotate(
        avg_rating=Avg('ratings__rating'),
        rating_count=Count('ratings', distinct=True),
        endorsement_count=Count('endorsements', distinct=True),
        review_count=Count('reviews', distinct=True),
    )


def _viewer_verified(request):
    """True when OAuth completed with guilds scope (session has guild id list)."""
    return get_viewer(request) is not None and GUILD_IDS_SESSION_KEY in request.session


def _require_guild_access(request, guild_id):
    """Redirect to index if viewer missing or guild not in their OAuth list."""
    if not viewer_can_access_guild(request, guild_id):
        return HttpResponseRedirect(reverse('movienights:index'))
    return None


def guild_index(request):
    viewer = get_viewer(request)
    verified = _viewer_verified(request)
    guilds = []
    if verified:
        guild_ids = get_viewer_guild_ids(request)
        if guild_ids:
            guilds = list(
                Guild.objects
                .filter(id__in=guild_ids)
                .annotate(movie_count=Count('movies'))
                .order_by('-date', 'id')
            )

    oauth_error = request.GET.get('oauth_error', '')
    oauth_warning = request.GET.get('oauth_warning', '')
    return render(request, 'movienights/guild_index.html', {
        'guilds': guilds,
        'viewer': viewer if verified else None,
        'verified': verified,
        'oauth_configured': oauth_configured(),
        'oauth_error': oauth_error,
        'oauth_error_message': OAUTH_ERROR_MESSAGES.get(
            oauth_error,
            f'Discord verification failed ({oauth_error}).' if oauth_error else '',
        ),
        'oauth_warning': oauth_warning,
        'background_grid_class': 'background-grid background-grid-medium',
    })


def guild_hub(request, guild_id):
    denied = _require_guild_access(request, guild_id)
    if denied:
        return denied
    guild = get_object_or_404(Guild, pk=guild_id)
    viewer = get_viewer(request)
    q = (request.GET.get('q') or '').strip()

    movies = (
        Movie.objects
        .filter(guild=guild)
        .select_related('user')
        .order_by('-date_suggested', 'title')
    )
    if q:
        movies = movies.filter(title__icontains=q)

    paginator = Paginator(movies, 20)
    page = request.GET.get('page') or 1
    page_obj = paginator.page(page)

    ctx = {
        'guild': guild,
        'viewer': viewer,
        'q': q,
        'movies': page_obj,
        'page_obj': page_obj,
        'background_grid_class': 'background-grid background-grid-medium',
    }
    ctx.update(_flash_context(request, ('suggest', 'remove')))
    return render(request, 'movienights/guild_hub.html', ctx)


@require_POST
def clear_viewer_view(request):
    next_url = safe_next_path(
        request.POST.get('next'),
        reverse('movienights:index'),
    )
    clear_viewer(request)
    response = HttpResponseRedirect(next_url)
    response.delete_cookie(COOKIE_NAME)
    return response


@require_GET
def discord_oauth_start(request):
    if not oauth_configured():
        return HttpResponseRedirect(
            reverse('movienights:index') + '?oauth_error=not_configured'
        )
    fallback = reverse('movienights:index')
    next_url = safe_next_path(request.GET.get('next'), fallback)
    state = new_oauth_state()
    request.session[SESSION_STATE_KEY] = state
    request.session[SESSION_NEXT_KEY] = next_url
    return HttpResponseRedirect(authorize_url(state))


@require_GET
def discord_oauth_callback(request):
    fallback = reverse('movienights:index')
    next_url = safe_next_path(
        request.session.pop(SESSION_NEXT_KEY, None),
        fallback,
    )
    expected_state = request.session.pop(SESSION_STATE_KEY, None)
    got_state = request.GET.get('state', '')
    if not expected_state or got_state != expected_state:
        return HttpResponseRedirect(next_url + _oauth_qs(next_url, 'oauth_error=bad_state'))

    if request.GET.get('error'):
        return HttpResponseRedirect(next_url + _oauth_qs(next_url, 'oauth_error=denied'))

    code = request.GET.get('code', '').strip()
    if not code:
        return HttpResponseRedirect(next_url + _oauth_qs(next_url, 'oauth_error=missing_code'))

    try:
        token = exchange_code(code)
        profile = fetch_discord_user(token)
        discord_guilds = fetch_discord_guilds(token)
        user, warning = upsert_discord_user_from_oauth(profile)
        guild_ids = sync_guilds_from_oauth(discord_guilds)
    except DiscordOAuthError as exc:
        key = 'oauth_failed'
        msg = str(exc).lower()
        if 'not in the movie database' in msg:
            key = 'no_user_row'
        elif 'client credentials' in msg:
            key = 'bad_credentials'
        return HttpResponseRedirect(next_url + _oauth_qs(next_url, f'oauth_error={key}'))

    set_viewer(request, user)
    set_viewer_guild_ids(request, guild_ids)
    redirect_to = next_url
    if warning:
        redirect_to = next_url + _oauth_qs(next_url, 'oauth_warning=name_write_failed')
    response = HttpResponseRedirect(redirect_to)
    response.set_cookie(
        COOKIE_NAME,
        str(user.id),
        max_age=COOKIE_MAX_AGE,
        samesite='Lax',
    )
    return response


def _oauth_qs(next_url: str, fragment: str) -> str:
    sep = '&' if '?' in next_url else '?'
    return sep + fragment


def _parse_mine(raw) -> str:
    """Return '', 'yes', or 'no' for the three-state by-me filter."""
    value = (raw or '').strip().lower()
    if value in ('1', 'true', 'yes', 'on'):
        return 'yes'
    if value in ('0', 'false', 'no', 'not'):
        return 'no'
    return ''


def _resolve_sort(view: str, sort: str, direction: str):
    cfg = VIEW_SORTS[view]
    default_sort, default_dir = cfg['default']
    if sort not in cfg['fields']:
        sort = default_sort
    if direction not in ('asc', 'desc'):
        direction = default_dir
    field = cfg['fields'][sort]
    order = field if direction == 'asc' else f'-{field}'
    return sort, direction, order


def _next_sort_dirs(view: str, sort: str, direction: str):
    """For each sortable column: dir to use when that header is clicked."""
    out = {}
    for key in VIEW_SORTS[view]['fields']:
        if key == sort and direction == 'desc':
            out[key] = 'asc'
        else:
            out[key] = 'desc'
    return out


def movie_list(request, guild_id):
    denied = _require_guild_access(request, guild_id)
    if denied:
        return denied
    guild = get_object_or_404(Guild, pk=guild_id)
    viewer = get_viewer(request)
    view = request.GET.get('view', 'top')
    if view not in VIEW_LABELS:
        view = 'top'

    q = (request.GET.get('q') or '').strip()
    mine = _parse_mine(request.GET.get('mine'))
    sort, direction, order = _resolve_sort(
        view,
        request.GET.get('sort', ''),
        request.GET.get('dir', ''),
    )

    movies = _annotate_movies(
        Movie.objects.filter(guild=guild).select_related('user')
    )

    if view == 'unwatched':
        movies = movies.filter(Q(watched=0) | Q(watched__isnull=True))
    else:
        movies = movies.filter(watched=1)

    if q:
        movies = movies.filter(title__icontains=q)

    if mine and viewer is not None:
        if view == 'top':
            by_me = Exists(
                Rating.objects.filter(movie_id=OuterRef('pk'), user_id=viewer.id)
            )
        else:
            by_me = Exists(
                Endorsement.objects.filter(movie_id=OuterRef('pk'), user_id=viewer.id)
            )
        if mine == 'yes':
            movies = movies.filter(by_me)
        else:
            movies = movies.filter(~by_me)

    movies = movies.order_by(order, 'title')

    paginator = Paginator(movies, 20)
    page = request.GET.get('page') or 1
    page_obj = paginator.page(page)

    return render(request, 'movienights/movie_list.html', {
        'guild': guild,
        'movies': page_obj,
        'page_obj': page_obj,
        'view': view,
        'view_label': VIEW_LABELS[view],
        'viewer': viewer,
        'q': q,
        'mine': mine,
        'sort': sort,
        'dir': direction,
        'next_dirs': _next_sort_dirs(view, sort, direction),
        'background_grid_class': 'background-grid background-grid-medium',
    })


def movie_detail(request, guild_id, movie_id):
    denied = _require_guild_access(request, guild_id)
    if denied:
        return denied
    guild = get_object_or_404(Guild, pk=guild_id)
    viewer = get_viewer(request)
    movie = get_object_or_404(
        _annotate_movies(Movie.objects.select_related('user', 'guild')),
        pk=movie_id,
        guild=guild,
    )
    ratings = (
        Rating.objects.filter(movie=movie)
        .select_related('user')
        .order_by('-date')
    )
    endorsements = (
        Endorsement.objects.filter(movie=movie)
        .select_related('user')
        .order_by('-date')
    )
    reviews = (
        Review.objects.filter(movie=movie)
        .select_related('user')
        .order_by('-date')
    )

    viewer_review = None
    viewer_rating = None
    viewer_has_endorsed = False
    if viewer is not None:
        viewer_review = next((r for r in reviews if r.user_id == viewer.id), None)
        viewer_rating = next((r for r in ratings if r.user_id == viewer.id), None)
        viewer_has_endorsed = any(e.user_id == viewer.id for e in endorsements)

    ctx = {
        'guild': guild,
        'movie': movie,
        'ratings': ratings,
        'endorsements': endorsements,
        'reviews': reviews,
        'viewer': viewer,
        'viewer_review': viewer_review,
        'viewer_rating': viewer_rating,
        'viewer_has_rated': viewer_rating is not None,
        'viewer_has_endorsed': viewer_has_endorsed,
        'background_grid_class': 'background-grid background-grid-medium',
    }
    ctx.update(_flash_context(
        request,
        (
            'rating', 'review', 'endorse', 'unendorse',
            'remove', 'transfer', 'date', 'suggest', 'rename',
        ),
        title=movie.title,
    ))
    return render(request, 'movienights/movie_detail.html', ctx)


REVIEW_MAX_LEN = actions.REVIEW_MAX_LEN


@require_GET
def movie_edit(request, guild_id, movie_id):
    denied = _require_guild_access(request, guild_id)
    if denied:
        return denied
    detail = reverse('movienights:movie_detail', args=[guild_id, movie_id])
    viewer, guild, auth_denied = _member_or_redirect(
        request, guild_id, detail, 'rename_error',
    )
    if auth_denied:
        return auth_denied
    movie = get_object_or_404(
        Movie.objects.select_related('user'),
        pk=movie_id,
        guild=guild,
    )
    edit_url = reverse('movienights:movie_edit', args=[guild_id, movie_id])
    ctx = {
        'guild': guild,
        'movie': movie,
        'viewer': viewer,
        'edit_url': edit_url,
        'background_grid_class': 'background-grid background-grid-medium',
    }
    ctx.update(_flash_context(
        request,
        ('rename', 'date', 'transfer', 'remove'),
        title=movie.title,
    ))
    return render(request, 'movienights/movie_edit.html', ctx)


@require_GET
def movie_review_edit(request, guild_id, movie_id):
    denied = _require_guild_access(request, guild_id)
    if denied:
        return denied
    detail = reverse('movienights:movie_detail', args=[guild_id, movie_id])
    viewer, guild, auth_denied = _member_or_redirect(
        request, guild_id, detail, 'review_error',
    )
    if auth_denied:
        return auth_denied
    movie = get_object_or_404(Movie, pk=movie_id, guild=guild)
    if not movie.watched:
        return _redirect_with(detail, review_error=Code.REVIEW_UNWATCHED.value)
    viewer_rating = Rating.objects.filter(movie=movie, user=viewer).first()
    if viewer_rating is None:
        return _redirect_with(detail, review_error='need_rating')
    viewer_review = Review.objects.filter(movie=movie, user=viewer).first()
    ctx = {
        'guild': guild,
        'movie': movie,
        'viewer': viewer,
        'viewer_review': viewer_review,
        'review_max_len': REVIEW_MAX_LEN,
        'background_grid_class': 'background-grid background-grid-medium',
    }
    ctx.update(_flash_context(request, ('review',), title=movie.title))
    return render(request, 'movienights/movie_review_edit.html', ctx)


def _redirect_with(url: str, **params) -> HttpResponseRedirect:
    parts = [f'{k}={v}' for k, v in params.items() if v is not None and v != '']
    if not parts:
        return HttpResponseRedirect(url)
    return HttpResponseRedirect(url + _oauth_qs(url, '&'.join(parts)))


def _member_or_redirect(request, guild_id, fallback_url: str, error_key: str = 'error'):
    """Return (viewer, guild, None) or (None, None, redirect)."""
    viewer, auth_err = actions.require_member(request, guild_id)
    if auth_err is not None:
        if auth_err.code == Code.NEED_ACCESS:
            return None, None, HttpResponseRedirect(reverse('movienights:index'))
        return None, None, _redirect_with(fallback_url, **{error_key: auth_err.code.value})
    guild = get_object_or_404(Guild, pk=guild_id)
    return viewer, guild, None


def _result_redirect(url: str, result: Result, prefix: str) -> HttpResponseRedirect:
    if result.ok:
        params = {f'{prefix}_saved': '1', f'{prefix}_code': result.code.value}
        if result.code == Code.RETURNED_TO_SUGGESTIONS:
            params[f'{prefix}_removed'] = '1'
        return _redirect_with(url, **params)
    return _redirect_with(url, **{f'{prefix}_error': result.code.value})


def _movie_payload(m: Movie) -> dict:
    return {
        'id': m.id,
        'title': m.title,
        'watched': bool(m.watched),
        'user_id': m.user_id,
        'user': m.user.display_name if m.user_id else None,
        'date_suggested': m.date_suggested.isoformat() if m.date_suggested else None,
        'date_watched': m.date_watched.isoformat() if m.date_watched else None,
        'avg_rating': getattr(m, 'avg_rating', None),
        'rating_count': getattr(m, 'rating_count', None),
        'endorsement_count': getattr(m, 'endorsement_count', None),
    }


@require_POST
def movie_suggest(request, guild_id):
    hub = reverse('movienights:guild_hub', args=[guild_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, hub, 'suggest_error')
    if denied:
        return denied
    title = (request.POST.get('title') or '').strip()
    result = actions.suggest(guild, viewer, title)
    next_url = safe_next_path(request.POST.get('next'), hub)
    return _result_redirect(next_url, result, 'suggest')


@require_POST
def movie_remove(request, guild_id):
    hub = reverse('movienights:guild_hub', args=[guild_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, hub, 'remove_error')
    if denied:
        return denied
    movie_id = request.POST.get('movie_id')
    title = (request.POST.get('title') or '').strip()
    try:
        mid = int(movie_id) if movie_id else None
    except (TypeError, ValueError):
        mid = None
    result = actions.remove_suggestion(guild, title=title, movie_id=mid)
    next_url = safe_next_path(request.POST.get('next'), hub)
    return _result_redirect(next_url, result, 'remove')


@require_POST
def movie_endorse(request, guild_id, movie_id):
    detail = reverse('movienights:movie_detail', args=[guild_id, movie_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, detail, 'endorse_error')
    if denied:
        return denied
    movie = get_object_or_404(Movie, pk=movie_id, guild=guild)
    result = actions.endorse(guild, movie, viewer)
    next_url = safe_next_path(request.POST.get('next'), detail)
    return _result_redirect(next_url, result, 'endorse')


@require_POST
def movie_unendorse(request, guild_id, movie_id):
    detail = reverse('movienights:movie_detail', args=[guild_id, movie_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, detail, 'unendorse_error')
    if denied:
        return denied
    movie = get_object_or_404(Movie, pk=movie_id, guild=guild)
    result = actions.unendorse(guild, movie, viewer)
    next_url = safe_next_path(request.POST.get('next'), detail)
    return _result_redirect(next_url, result, 'unendorse')


@require_POST
def movie_review(request, guild_id, movie_id):
    detail = reverse('movienights:movie_detail', args=[guild_id, movie_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, detail, 'review_error')
    if denied:
        return denied
    movie = get_object_or_404(Movie, pk=movie_id, guild=guild)
    result = actions.review(guild, movie, viewer, request.POST.get('review_text', ''))
    next_url = safe_next_path(request.POST.get('next'), detail)
    # Preserve legacy query keys expected by movie_detail template.
    if result.ok:
        return _redirect_with(next_url, review_saved='1')
    legacy = {
        Code.NEED_VIEWER: 'need_viewer',
        Code.NEED_RATING: 'need_rating',
        Code.REVIEW_UNWATCHED: 'unwatched',
        Code.REVIEW_EMPTY: 'empty',
        Code.REVIEW_TOO_LONG: 'too_long',
        Code.DB_ERROR: 'save_failed',
    }
    return _redirect_with(next_url, review_error=legacy.get(result.code, result.code.value))


@require_POST
def movie_rate(request, guild_id, movie_id):
    detail = reverse('movienights:movie_detail', args=[guild_id, movie_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, detail, 'rating_error')
    if denied:
        return denied
    movie = get_object_or_404(Movie, pk=movie_id, guild=guild)
    action = (request.POST.get('action') or 'save').strip().lower()
    next_url = safe_next_path(request.POST.get('next'), detail)

    if action == 'remove':
        result = actions.unrate(guild, movie, viewer)
        if result.ok:
            return _redirect_with(next_url, rating_removed='1')
        legacy = {
            Code.NOT_RATED: 'missing',
            Code.NEED_VIEWER: 'need_viewer',
            Code.DB_ERROR: 'save_failed',
        }
        return _redirect_with(next_url, rating_error=legacy.get(result.code, result.code.value))

    result = actions.rate(guild, movie, viewer, request.POST.get('rating', ''))
    if result.ok:
        return _redirect_with(next_url, rating_saved='1')
    legacy = {
        Code.RATING_INVALID: 'invalid',
        Code.RATING_RANGE: 'range',
        Code.NEED_VIEWER: 'need_viewer',
        Code.DB_ERROR: 'save_failed',
    }
    return _redirect_with(next_url, rating_error=legacy.get(result.code, result.code.value))


@require_POST
def movie_rename(request, guild_id, movie_id):
    edit = reverse('movienights:movie_edit', args=[guild_id, movie_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, edit, 'rename_error')
    if denied:
        return denied
    movie = get_object_or_404(Movie, pk=movie_id, guild=guild)
    result = actions.rename(guild, movie, request.POST.get('title', ''))
    next_url = safe_next_path(request.POST.get('next'), edit)
    return _result_redirect(next_url, result, 'rename')


@require_POST
def movie_transfer(request, guild_id, movie_id):
    edit = reverse('movienights:movie_edit', args=[guild_id, movie_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, edit, 'transfer_error')
    if denied:
        return denied
    movie = get_object_or_404(Movie, pk=movie_id, guild=guild)
    next_url = safe_next_path(request.POST.get('next'), edit)
    try:
        target_id = int(request.POST.get('user_id') or '')
    except (TypeError, ValueError):
        return _redirect_with(next_url, transfer_error=Code.USER_NOT_FOUND.value)
    result = actions.transfer(guild, movie, target_id)
    return _result_redirect(next_url, result, 'transfer')


@require_POST
def movie_change_date_watched(request, guild_id, movie_id):
    edit = reverse('movienights:movie_edit', args=[guild_id, movie_id])
    viewer, guild, denied = _member_or_redirect(request, guild_id, edit, 'date_error')
    if denied:
        return denied
    movie = get_object_or_404(Movie, pk=movie_id, guild=guild)
    result = actions.change_date_watched(
        guild, movie, request.POST.get('date_watched', ''),
    )
    next_url = safe_next_path(request.POST.get('next'), edit)
    return _result_redirect(next_url, result, 'date')


@require_GET
def api_list(request, guild_id, kind):
    """Temporary JSON verify endpoints for browse/query helpers."""
    denied = _require_guild_access(request, guild_id)
    if denied:
        return JsonResponse({'error': 'access_denied'}, status=403)
    guild = get_object_or_404(Guild, pk=guild_id)
    user = None
    user_id = request.GET.get('user_id')
    if user_id:
        try:
            user = DiscordUser.objects.filter(pk=int(user_id)).first()
        except (TypeError, ValueError):
            return JsonResponse({'error': 'bad_user_id'}, status=400)

    q = (request.GET.get('q') or '').strip()
    handlers = {
        'suggestions': lambda: list(queries.suggestions(guild, user)[:50]),
        'endorsed': lambda: list(queries.endorsed_by(guild, user)[:50]) if user else [],
        'movienights': lambda: list(queries.movienights(guild, user)[:50]),
        'top_movienights': lambda: list(queries.top_movienights(guild, user)[:50]),
        'unrated': lambda: list(queries.unrated(guild, user)[:50]) if user else [],
        'random': lambda: (
            [m] if (m := queries.random_suggestion(guild)) is not None else []
        ),
        'find_movies': lambda: list(queries.find_movies(guild, q)[:50]),
    }
    if kind == 'seen':
        return JsonResponse({'count': queries.seen_count(guild)})
    if kind == 'standings':
        return JsonResponse({'results': [
            {
                'user_id': r['user_id'],
                'display_name': r['display_name'],
                'movie_count': r['movie_count'],
                'mean_avg': r['mean_avg'],
            }
            for r in queries.standings(guild)
        ]})
    if kind == 'attendance':
        biggest = request.GET.get('order', 'biggest') != 'smallest'
        return JsonResponse({'results': [
            {
                'movie_id': r['movie'].id,
                'title': r['title'],
                'rating_count': r['rating_count'],
            }
            for r in queries.attendance(guild, biggest=biggest)
        ]})
    if kind == 'ratings':
        if user is None:
            return JsonResponse({'error': 'user_id_required'}, status=400)
        return JsonResponse({'results': [
            {
                'movie_id': r.movie_id,
                'title': r.movie.title,
                'rating': r.rating,
            }
            for r in queries.ratings_for_user(guild, user)[:50]
        ]})
    if kind == 'reviews':
        revs = queries.reviews_search(guild, q)
        return JsonResponse({'results': [
            {
                'movie_id': r.movie_id,
                'title': r.movie.title if r.movie_id else None,
                'user': r.user.display_name,
                'text': r.review_text,
            }
            for r in revs[:50]
        ]})
    if kind == 'find_users':
        return JsonResponse({'results': [
            {'id': u.id, 'display_name': u.display_name}
            for u in queries.find_users(guild, q)[:50]
        ]})
    if kind == 'endorsements':
        if user is None:
            return JsonResponse({'error': 'user_id_required'}, status=400)
        return JsonResponse({'results': [
            {
                'movie_id': e.movie_id,
                'title': e.movie.title if e.movie_id else None,
                'date': e.date.isoformat() if e.date else None,
            }
            for e in queries.endorsements_for_user(guild, user)[:50]
        ]})
    if kind not in handlers:
        return JsonResponse({'error': 'unknown_kind'}, status=404)
    if kind in ('endorsed', 'unrated') and user is None:
        return JsonResponse({'error': 'user_id_required'}, status=400)
    movies = [m for m in handlers[kind]() if m is not None]
    return JsonResponse({'results': [_movie_payload(m) for m in movies]})
