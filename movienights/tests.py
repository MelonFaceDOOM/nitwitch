"""Unit tests for movienights domain actions (mocked ORM — no live DB)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from movienights.actions import (
    Code,
    change_date_watched,
    endorse,
    rate,
    remove_suggestion,
    rename,
    review,
    suggest,
    transfer,
    unendorse,
    unrate,
)


def _user(uid=1, name='alice'):
    u = MagicMock()
    u.id = uid
    u.pk = uid
    u.display_name = name
    return u


def _guild(gid=10):
    g = MagicMock()
    g.id = gid
    g.pk = gid
    return g


def _movie(*, mid=100, title='Alien', watched=0, user_id=1, date_watched=None):
    m = MagicMock()
    m.id = mid
    m.pk = mid
    m.title = title
    m.watched = watched
    m.user_id = user_id
    m.is_watched = bool(watched)
    m.date_watched = date_watched
    m.user = _user(user_id)
    return m


class SuggestTests(SimpleTestCase):
    @patch('movienights.actions.Movie.objects')
    def test_suggest_new_movie(self, movie_qs):
        movie_qs.filter.return_value.select_related.return_value.first.return_value = None
        created = _movie(title='Alien')
        movie_qs.create.return_value = created
        guild, user = _guild(), _user()

        result = suggest(guild, user, 'Alien')

        self.assertTrue(result.ok)
        self.assertEqual(result.code, Code.OK)
        self.assertIn('has been added', result.message)
        kwargs = movie_qs.create.call_args.kwargs
        self.assertEqual(kwargs['title'], 'Alien')
        self.assertEqual(kwargs['watched'], 0)
        self.assertIsNotNone(kwargs['date_suggested'])

    @patch('movienights.actions.endorse')
    @patch('movienights.actions.Movie.objects')
    def test_suggest_existing_suggestion_auto_endorses(self, movie_qs, endorse_fn):
        existing = _movie(watched=0, user_id=99)
        movie_qs.filter.return_value.select_related.return_value.first.return_value = existing
        endorse_fn.return_value = MagicMock(ok=True, code=Code.OK, message="endorsed")

        result = suggest(_guild(), _user(1), 'Alien')

        endorse_fn.assert_called_once()
        self.assertTrue(result.ok)

    @patch('movienights.actions.Movie.objects')
    def test_suggest_existing_watched_rejected(self, movie_qs):
        existing = _movie(watched=1, title='Alien')
        movie_qs.filter.return_value.select_related.return_value.first.return_value = existing

        result = suggest(_guild(), _user(), 'Alien')

        self.assertFalse(result.ok)
        self.assertEqual(result.code, Code.ALREADY_RATED)


class RemoveTests(SimpleTestCase):
    @patch('movienights.actions.Movie.objects')
    def test_cannot_remove_watched(self, movie_qs):
        existing = _movie(watched=1, title='Alien')
        movie_qs.filter.return_value.select_related.return_value.first.return_value = existing

        result = remove_suggestion(_guild(), title='Alien')

        self.assertEqual(result.code, Code.CANT_REMOVE_WATCHED)


class EndorseTests(SimpleTestCase):
    @patch('movienights.actions.Endorsement.objects')
    def test_cannot_endorse_own(self, end_qs):
        movie = _movie(watched=0, user_id=1)
        user = _user(1)

        result = endorse(_guild(), movie, user)

        self.assertEqual(result.code, Code.CANT_ENDORSE_OWN)
        end_qs.create.assert_not_called()

    @patch('movienights.actions.Endorsement.objects')
    def test_cannot_double_endorse(self, end_qs):
        movie = _movie(watched=0, user_id=2)
        end_qs.filter.return_value.exists.return_value = True

        result = endorse(_guild(), movie, _user(1))

        self.assertEqual(result.code, Code.ALREADY_ENDORSED)

    @patch('movienights.actions.Endorsement.objects')
    def test_cannot_endorse_watched(self, end_qs):
        movie = _movie(watched=1, user_id=2)

        result = endorse(_guild(), movie, _user(1))

        self.assertEqual(result.code, Code.CANT_ENDORSE_WATCHED)

    @patch('movienights.actions.Endorsement.objects')
    def test_endorse_ok(self, end_qs):
        movie = _movie(watched=0, user_id=2)
        end_qs.filter.return_value.exists.return_value = False

        result = endorse(_guild(), movie, _user(1))

        self.assertTrue(result.ok)
        end_qs.create.assert_called_once()
        self.assertIsNotNone(end_qs.create.call_args.kwargs['date'])


class UnendorseTests(SimpleTestCase):
    @patch('movienights.actions.Endorsement.objects')
    def test_unendorse_missing(self, end_qs):
        end_qs.filter.return_value.delete.return_value = (0, {})

        result = unendorse(_guild(), _movie(), _user())

        self.assertEqual(result.code, Code.NOT_ENDORSED)


class RateTests(SimpleTestCase):
    @patch('movienights.actions.Rating.objects')
    def test_rating_out_of_range(self, rating_qs):
        result = rate(_guild(), _movie(watched=0), _user(), '11')
        self.assertEqual(result.code, Code.RATING_RANGE)
        rating_qs.create.assert_not_called()

    @patch('movienights.actions.Rating.objects')
    def test_rating_invalid(self, rating_qs):
        result = rate(_guild(), _movie(), _user(), 'nope')
        self.assertEqual(result.code, Code.RATING_INVALID)

    @patch('movienights.actions.Rating.objects')
    def test_rate_promotes_suggestion(self, rating_qs):
        movie = _movie(watched=0, date_watched=None)
        rating_qs.filter.return_value.first.return_value = None

        result = rate(_guild(), movie, _user(), '8.5')

        self.assertTrue(result.ok)
        self.assertEqual(movie.watched, 1)
        self.assertIsNotNone(movie.date_watched)
        movie.save.assert_called()
        kwargs = rating_qs.create.call_args.kwargs
        self.assertEqual(kwargs['rating'], 8.5)
        self.assertIsNotNone(kwargs['date'])

    @patch('movienights.actions.Rating.objects')
    def test_rate_slash_ten_suffix(self, rating_qs):
        movie = _movie(watched=1, date_watched=timezone.now())
        rating_qs.filter.return_value.first.return_value = None

        result = rate(_guild(), movie, _user(), '7/10')

        self.assertTrue(result.ok)
        self.assertEqual(rating_qs.create.call_args.kwargs['rating'], 7.0)


class UnrateTests(SimpleTestCase):
    @patch('movienights.actions.Review.objects')
    @patch('movienights.actions.Rating.objects')
    def test_last_rating_returns_to_suggestions(self, rating_qs, review_qs):
        movie = _movie(watched=1, title='Alien')
        rating_qs.filter.return_value.delete.return_value = (1, {})
        # Second filter().exists() for remaining ratings → False
        rating_qs.filter.return_value.exists.return_value = False
        review_qs.filter.return_value.delete.return_value = (1, {})

        result = unrate(_guild(), movie, _user())

        self.assertEqual(result.code, Code.RETURNED_TO_SUGGESTIONS)
        self.assertEqual(movie.watched, 0)
        self.assertIsNone(movie.date_watched)
        self.assertTrue(result.data.get('returned_to_suggestions'))
        review_qs.filter.assert_called()
        review_qs.filter.return_value.delete.assert_called_once()

    @patch('movienights.actions.Rating.objects')
    def test_unrate_not_rated(self, rating_qs):
        rating_qs.filter.return_value.delete.return_value = (0, {})

        result = unrate(_guild(), _movie(title='Alien'), _user())

        self.assertEqual(result.code, Code.NOT_RATED)

    @patch('movienights.actions.Review.objects')
    @patch('movienights.actions.Rating.objects')
    def test_unrate_deletes_review(self, rating_qs, review_qs):
        movie = _movie(watched=1, title='Alien')
        rating_qs.filter.return_value.delete.return_value = (1, {})
        rating_qs.filter.return_value.exists.return_value = True
        review_qs.filter.return_value.delete.return_value = (1, {})

        result = unrate(_guild(), movie, _user())

        self.assertTrue(result.ok)
        review_qs.filter.return_value.delete.assert_called_once()


class ReviewTests(SimpleTestCase):
    @patch('movienights.actions.Review.objects')
    @patch('movienights.actions.Rating.objects')
    def test_need_rating_first(self, rating_qs, review_qs):
        rating_qs.filter.return_value.exists.return_value = False
        movie = _movie(watched=1)

        result = review(_guild(), movie, _user(), 'great')

        self.assertEqual(result.code, Code.NEED_RATING)
        review_qs.create.assert_not_called()

    @patch('movienights.actions.Review.objects')
    @patch('movienights.actions.Rating.objects')
    def test_review_ok_sets_date(self, rating_qs, review_qs):
        rating_qs.filter.return_value.exists.return_value = True
        review_qs.filter.return_value.first.return_value = None
        movie = _movie(watched=1, title='Alien')

        result = review(_guild(), movie, _user(), 'great film')

        self.assertTrue(result.ok)
        self.assertIsNotNone(review_qs.create.call_args.kwargs['date'])


class TransferTests(SimpleTestCase):
    @patch('movienights.actions.DiscordUser.objects')
    def test_user_not_found(self, user_qs):
        user_qs.filter.return_value.first.return_value = None

        result = transfer(_guild(), _movie(), 999)

        self.assertEqual(result.code, Code.USER_NOT_FOUND)

    @patch('movienights.actions.DiscordUser.objects')
    def test_already_owned(self, user_qs):
        target = _user(5, 'bob')
        user_qs.filter.return_value.first.return_value = target
        movie = _movie(user_id=5)

        result = transfer(_guild(), movie, 5)

        self.assertEqual(result.code, Code.ALREADY_OWNED)


class ChangeDateTests(SimpleTestCase):
    def test_bad_date(self):
        result = change_date_watched(_guild(), _movie(), '31-12-2024')
        self.assertEqual(result.code, Code.BAD_DATE)

    def test_ok_date(self):
        movie = _movie()
        result = change_date_watched(_guild(), movie, '2024-12-31')
        self.assertTrue(result.ok)
        movie.save.assert_called_once()
        self.assertIsInstance(movie.date_watched, datetime)


class RenameTests(SimpleTestCase):
    def test_empty_title(self):
        result = rename(_guild(), _movie(), '  ')
        self.assertEqual(result.code, Code.TITLE_EMPTY)

    @patch('movienights.actions._find_movie', return_value=None)
    def test_rename_ok(self, _find):
        movie = _movie(title='Old')
        result = rename(_guild(), movie, 'New Title')
        self.assertTrue(result.ok)
        self.assertEqual(movie.title, 'New Title')
        movie.save.assert_called_once()

    @patch('movienights.actions._find_movie')
    def test_title_taken(self, find_movie):
        other = _movie(mid=99, title='Taken')
        find_movie.return_value = other
        result = rename(_guild(), _movie(mid=1, title='Old'), 'Taken')
        self.assertEqual(result.code, Code.TITLE_TAKEN)
