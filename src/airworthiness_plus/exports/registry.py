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
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Counter, UtilisationEntry
from airworthiness_plus.components.models import Component, Installation
from airworthiness_plus.configuration.models import Baseline, Position, Transfer, TransferItem
from airworthiness_plus.contracts.models import Contract, WorkOrder
from airworthiness_plus.customers.models import Customer
from airworthiness_plus.defects.models import Defect, RepeatAction
from airworthiness_plus.directives.models import Applicability, Compliance, Directive, Source
from airworthiness_plus.imports.models import Load, LoadedValue, ValueCheck
from airworthiness_plus.logistics.models import (
    Receipt,
    ReceivingCheck,
    ReceivingDisposition,
    StockEntry,
    SubcontractorAssessment,
    Supplier,
    SupplierEvaluation,
)
from airworthiness_plus.maintenance_data.models import AmendmentCheck, DataSet, Revision
from airworthiness_plus.modifications.models import Bulletin, Change, Weighing, WeightSchedule
from airworthiness_plus.organisations.models import Approval, Organisation
from airworthiness_plus.people.models import (
    ExperienceEvidence,
    ExperienceWithdrawal,
    MaintenanceAuthorisation,
    MaintenanceAuthorisationWithdrawal,
    Person,
    RecurrentTraining,
)
from airworthiness_plus.planning.models import (
    WorkCard,
    WorkCardAttestation,
    WorkCardSigningJob,
    WorkPackage,
)
from airworthiness_plus.programme.models import (
    AnnualReview,
    Departure,
    Programme,
    Task,
    WorkDone,
)
from airworthiness_plus.releases.models import HistoricalReleaseEvidence, Release
from airworthiness_plus.reviews.models import (
    Certificate,
    Extension,
    Review,
    ReviewItem,
    ReviewStaff,
)
from airworthiness_plus.sample.models import Added
from airworthiness_plus.staffing.models import Absence, Demand, Report
from airworthiness_plus.staffing.models import Review as StaffingReview
from airworthiness_plus.staffing.roster_models import (
    BankHoliday,
    Handover,
    PublishedRoster,
    PublishedShift,
    Settings,
    Shift,
    ShiftPattern,
    StaffingMinimum,
)
from airworthiness_plus.tooling.calibration_models import (
    CalibrationCertificate,
    CalibrationMovement,
    CalibrationOrder,
    CalibrationReinstatement,
    CalibrationResult,
    CertificateDecision,
    ToolImpactCase,
    ToolServiceProviderAuthorisation,
)
from airworthiness_plus.tooling.models import (
    Tool,
    ToolControlEvent,
    ToolControlRevision,
    ToolDelegation,
    ToolDelegationWithdrawal,
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


def _maintenance_data(prefix: str = "") -> Callable[[Aircraft], Q]:
    # Maintenance data applies to an aircraft through its type rating.
    return lambda aircraft: (
        Q(**{f"{prefix}applies_to__contains": [aircraft.type_rating]})
        | Q(
            **{
                f"{prefix}pk__in": WorkCard.objects.filter(package__aircraft=aircraft).values(
                    "data_set_id"
                )
            }
        )
    )


REGISTRY: tuple[Exported, ...] = (
    Exported(Organisation, None),
    Exported(Approval, None),
    Exported(User, None),
    Exported(Person, None),
    Exported(MaintenanceAuthorisation, None),
    Exported(MaintenanceAuthorisationWithdrawal, None),
    Exported(ExperienceEvidence, None),
    Exported(ExperienceWithdrawal, None),
    Exported(RecurrentTraining, None),
    # The owner is part of the aircraft's record (REQ-208): every customer that
    # has ever owned it, so that the names in its history can be read
    # (independent review of 24 November 2026, finding 12).
    Exported(Customer, lambda aircraft: Q(pk__in=aircraft_services.every_owner(aircraft))),
    Exported(Aircraft, lambda aircraft: Q(pk=aircraft.pk)),
    Exported(Counter, _by("aircraft")),
    Exported(UtilisationEntry, _by("counter__aircraft")),
    Exported(Programme, _by("aircraft")),
    Exported(Task, _by("programme__aircraft")),
    Exported(WorkDone, _by("aircraft")),
    Exported(Departure, _by("programme__aircraft")),
    Exported(AnnualReview, _by("programme__aircraft")),
    Exported(Release, _by("work__aircraft")),
    Exported(HistoricalReleaseEvidence, _by("work__aircraft")),
    Exported(Contract, _by("aircraft")),
    Exported(WorkOrder, _by("aircraft")),
    Exported(WorkPackage, _by("aircraft")),
    Exported(WorkCard, _by("package__aircraft")),
    Exported(WorkCardAttestation, _by("card__package__aircraft")),
    Exported(WorkCardSigningJob, _by("card__package__aircraft")),
    Exported(Defect, _by("aircraft")),
    # What was done about the same defect on the aircraft's type.
    Exported(RepeatAction, lambda aircraft: Q(type_rating=aircraft.type_rating)),
    # Every component that has ever been fitted to the aircraft, and where each has been.
    Exported(Component, lambda aircraft: Q(installations__aircraft=aircraft)),
    Exported(Installation, lambda aircraft: Q(component__installations__aircraft=aircraft)),
    Exported(Bulletin, _by("aircraft")),
    Exported(Change, _by("aircraft")),
    Exported(Weighing, _by("aircraft")),
    Exported(WeightSchedule, _by("aircraft")),
    Exported(Transfer, _by("aircraft")),
    Exported(TransferItem, _by("transfer__aircraft")),
    Exported(Position, _by("aircraft")),
    Exported(Baseline, _by("aircraft")),
    Exported(Directive, _every),
    # The sources checked for directives are checked for every aircraft.
    Exported(Source, _every),
    Exported(Applicability, _by("aircraft")),
    Exported(Compliance, _by("applicability__aircraft")),
    Exported(DataSet, _maintenance_data()),
    Exported(Revision, _maintenance_data("data_set__")),
    Exported(AmendmentCheck, _maintenance_data("data_set__")),
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
    # That a part of the sample was added. Only a sample organisation has any.
    Exported(Added, None),
    Exported(Demand, None),
    Exported(StaffingReview, None),
    Exported(Supplier, None),
    Exported(SupplierEvaluation, None),
    Exported(Receipt, None),
    Exported(ReceivingCheck, None),
    Exported(ReceivingDisposition, None),
    Exported(StockEntry, None),
    Exported(SubcontractorAssessment, None),
    Exported(Tool, None),
    Exported(ToolServiceProviderAuthorisation, None),
    Exported(CalibrationOrder, None),
    Exported(CalibrationMovement, None),
    Exported(CalibrationCertificate, None),
    Exported(CalibrationResult, None),
    Exported(CertificateDecision, None),
    Exported(ToolImpactCase, None),
    Exported(CalibrationReinstatement, None),
    Exported(ToolControlRevision, None),
    Exported(ToolControlEvent, None),
    Exported(ToolDelegation, None),
    Exported(ToolDelegationWithdrawal, None),
    Exported(Report, None),
    Exported(Absence, None),
    Exported(BankHoliday, None),
    Exported(ShiftPattern, None),
    Exported(StaffingMinimum, None),
    Exported(PublishedShift, None),
    Exported(Handover, _by("package__aircraft")),
    Exported(PublishedRoster, None),
    Exported(Settings, None),
    Exported(Shift, None),
)
