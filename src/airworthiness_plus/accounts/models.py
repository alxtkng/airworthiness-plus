"""The user record (REQ-005, REQ-010)."""

from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from airworthiness_plus.history.models import Record, RecordQuerySet
from airworthiness_plus.organisations.models import Organisation


class UserManager(BaseUserManager.from_queryset(RecordQuerySet)):  # type: ignore[misc]
    """Creates users. There is no superuser: no account sits above an organisation (REQ-004)."""

    def create_user(
        self,
        *,
        organisation: Organisation,
        username: str,
        full_name: str,
        password: str | None = None,
        **fields: Any,
    ) -> "User":
        """Create a named account in ``organisation``. With no password it cannot sign in."""
        user: User = self.model(
            organisation=organisation, username=username, full_name=full_name, **fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(Record, AbstractBaseUser):
    """One named person in one organisation.

    A user who leaves is made inactive, never deleted, and past entries in
    the history keep their name (REQ-010).
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="users")
    username = models.CharField(max_length=254, unique=True)
    full_name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self) -> str:
        return self.full_name
