from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from apps.accounts.session_policy import claim_exclusive_session, release_exclusive_session


@receiver(user_logged_in)
def claim_session_on_login(sender, request, user, **kwargs):
    if request is None:
        return
    claim_exclusive_session(request, user)


@receiver(user_logged_out)
def release_session_on_logout(sender, request, user, **kwargs):
    if request is None or user is None:
        return
    release_exclusive_session(request, user)
