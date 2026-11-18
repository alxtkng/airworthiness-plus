"""Application configuration."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """The accounts application."""

    name = "airworthiness_plus.accounts"

    def ready(self) -> None:
        """Stop Django writing the time of each sign-in to the user record.

        Sign-ins are entered in the access log (REQ-009). The user record,
        and so its history, changes only when the user does.
        """
        from django.contrib.auth.models import update_last_login
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.disconnect(update_last_login, dispatch_uid="update_last_login")
