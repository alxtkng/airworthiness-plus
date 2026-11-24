"""The user record and the access log (REQ-005 to REQ-010)."""

from typing import Any, ClassVar, NoReturn

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models import Q
from django.utils.crypto import salted_hmac

from airworthiness_plus.accounts.roles import Action, Role, permitted
from airworthiness_plus.history.models import Record, RecordQuerySet, RecordsAreNeverDeletedError
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
        """Create a named account in ``organisation``. With no password it cannot sign in.

        The account is a person's, so it is given its person record with it
        (REQ-204). The database refuses a sign-in that has none.
        """
        from airworthiness_plus.people.services import person_for

        user: User = self.model(
            organisation=organisation, username=username, full_name=full_name, **fields
        )
        user.set_password(password)
        with transaction.atomic():
            user.save(using=self._db)
            person_for(user)
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
    roles = ArrayField(models.CharField(max_length=40, choices=Role.choices), default=list)
    # The secret shared with the user's authenticator application. It is kept
    # out of the history. A user signs in only once it is confirmed (REQ-008).
    second_factor_secret = models.CharField(max_length=64, blank=True)
    second_factor_confirmed = models.BooleanField(default=False)
    # A password given by an Administrator is changed by the user before anything else.
    password_must_change = models.BooleanField(default=False)
    # The day a first password was given. It stops working after 7 days if it
    # has not been changed (OWASP ASVS 5.0, 6.4.1).
    first_password_set_on = models.DateField(null=True, blank=True)
    # Raised to end every session of the user at once (OWASP ASVS 5.0, 7.4.5, 7.5.2).
    session_generation = models.PositiveIntegerField(default=0)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(roles__contained_by=list(Role.values)),
                name="user_has_known_roles",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name

    def _get_session_auth_hash(self, secret: str | bytes | None = None) -> str:
        """Return what a session must carry to be this user's.

        It changes when the password changes and when the user's sessions
        are ended, so every session made before then stops working.
        """
        key_salt = "django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash"
        return salted_hmac(
            key_salt,
            f"{self.password}:{self.session_generation}",
            secret=secret,
            algorithm="sha256",
        ).hexdigest()

    def may(self, action: Action) -> bool:
        """Return whether this user may take ``action`` (REQ-006).

        An inactive user may do nothing. Otherwise any role the user holds
        that permits the action is enough.
        """
        return self.is_active and permitted(self.roles, action)


class AccessKind(models.TextChoices):
    """What an entry in the access log records (REQ-009)."""

    SIGNED_IN = "Signed In", "Signed In"
    SIGN_IN_FAILED = "Sign-In Failed", "Sign-In Failed"
    SIGN_IN_REFUSED_WHILE_LOCKED = "Sign-In Refused While Locked", "Sign-In Refused While Locked"
    SECOND_FACTOR_SET_UP = "Second Factor Set Up", "Second Factor Set Up"
    SIGNED_OUT = "Signed Out", "Signed Out"
    ACTION_REFUSED = "Action Refused", "Action Refused"
    RECORDS_EXPORTED = "Records Exported", "Records Exported"
    # These two are names of events, not passwords.
    PASSWORD_CHANGED = "Password Changed", "Password Changed"  # pragma: allowlist secret
    PASSWORD_RESET = (
        "Password Set by an Administrator",  # pragma: allowlist secret
        "Password Set by an Administrator",
    )
    SECOND_FACTOR_RESET = "Second Factor Reset", "Second Factor Reset"
    SESSIONS_ENDED = "Sessions Ended", "Sessions Ended"
    CODE_ACCEPTED = "Code Accepted", "Code Accepted"


class AccessEntry(models.Model):
    """One entry in the access log: a sign-in, a failed sign-in or a refused action.

    Entries are added and never changed or removed; the database refuses
    both. The time is set by the database. A failed sign-in with a user
    name that belongs to nobody has no organisation and no user.
    """

    organisation = models.ForeignKey(
        Organisation, on_delete=models.PROTECT, null=True, related_name="+"
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name="+")
    username = models.CharField(max_length=254)
    kind = models.CharField(max_length=40, choices=AccessKind.choices)
    detail = models.CharField(max_length=200, blank=True)
    at = models.DateTimeField(null=True)
    code_counter = models.BigIntegerField(null=True)
    address = models.GenericIPAddressField(null=True)

    objects = RecordQuerySet.as_manager()

    class Meta:
        ordering = ["id"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the entry. An entry that exists is never saved again."""
        if self.pk is not None:
            raise RecordsAreNeverDeletedError("The access log is never changed")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Refuse. The database refuses too, whoever asks."""
        raise RecordsAreNeverDeletedError("The access log is never deleted")
