"""Every type of record, and how each belongs to an aircraft (REQ-134 to REQ-136).

A type of record that is not listed here fails the build
(``tests/test_exports.py``), so that a new type cannot be added without
being exported (hazard H-012).
"""

from collections.abc import Callable
from dataclasses import dataclass

from django.db import models
from django.db.models import Q

from airworthiness_plus.acceptance.models import Problem, ProblemNote
from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.models import Aircraft, Counter, UtilisationEntry
from airworthiness_plus.directives.models import Applicability, Compliance, Directive
from airworthiness_plus.imports.models import Load, LoadedValue, ValueCheck
from airworthiness_plus.maintenance_data.models import AmendmentCheck, DataSet, Revision
from airworthiness_plus.organisations.models import Approval, Organisation
from airworthiness_plus.programme.models import Programme, Task, WorkDone
from airworthiness_plus.reviews.models import (
    Certificate,
    Extension,
    Review,
    ReviewItem,
    ReviewStaff,
)


@dataclass(frozen=True)
class Exported:
    """One type of record.

    ``of_aircraft`` gives the records of this type that belong to an
    aircraft. With none, the type is part of the organisation's record
    only.
    """

    model: type[models.Model]
    of_aircraft: Callable[[Aircraft], Q] | None

    @property
    def table(self) -> str:
        """Return the name of the table, which is the record type in the history."""
        return self.model._meta.db_table


def _by(lookup: str) -> Callable[[Aircraft], Q]:
    return lambda aircraft: Q(**{lookup: aircraft})


def _every(aircraft: Aircraft) -> Q:
    # Every directive the organisation records is assessed against every aircraft.
    return Q()


def _type_rating(lookup: str) -> Callable[[Aircraft], Q]:
    # Maintenance data applies to an aircraft through its type rating.
    return lambda aircraft: Q(**{lookup: [aircraft.type_rating]})


REGISTRY: tuple[Exported, ...] = (
    Exported(Organisation, None),
    Exported(Approval, None),
    Exported(User, None),
    Exported(Aircraft, lambda aircraft: Q(pk=aircraft.pk)),
    Exported(Counter, _by("aircraft")),
    Exported(UtilisationEntry, _by("counter__aircraft")),
    Exported(Programme, _by("aircraft")),
    Exported(Task, _by("programme__aircraft")),
    Exported(WorkDone, _by("aircraft")),
    Exported(Directive, _every),
    Exported(Applicability, _by("aircraft")),
    Exported(Compliance, _by("applicability__aircraft")),
    Exported(DataSet, _type_rating("applies_to__contains")),
    Exported(Revision, _type_rating("data_set__applies_to__contains")),
    Exported(AmendmentCheck, _type_rating("data_set__applies_to__contains")),
    Exported(ReviewStaff, None),
    Exported(Certificate, _by("aircraft")),
    Exported(Extension, _by("certificate__aircraft")),
    Exported(Review, _by("aircraft")),
    Exported(ReviewItem, _by("review__aircraft")),
    Exported(Problem, None),
    Exported(ProblemNote, None),
    Exported(Load, None),
    Exported(LoadedValue, None),
    Exported(ValueCheck, None),
)
