"""Central place for the site's admin gate.

The whole site treats "admin" as a single boolean: ``is_staff``. Superusers are
implicitly staff, so they count as admins too. Use ``admin_required`` on views
and ``user.is_staff`` in templates to keep everything consistent.
"""

from django.contrib.auth.decorators import user_passes_test


def is_admin(user) -> bool:
    return user.is_authenticated and user.is_staff


# Redirects anonymous/non-staff users to the login page.
admin_required = user_passes_test(is_admin)
