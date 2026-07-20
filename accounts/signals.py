"""Signup-time behavior.

On the dev machine we want a frictionless loop: signing up immediately gives you
a full admin account with no email confirmation. This is guarded strictly on
``config.DEV`` so it can never fire in production.
"""

import config
from allauth.account.signals import user_signed_up
from django.dispatch import receiver


@receiver(user_signed_up)
def grant_admin_on_dev_signup(request, user, **kwargs):
    if config.DEV:
        user.is_staff = True
        user.is_superuser = True
        user.save()
