"""The five illustrative Suppliers board records, for the primary sample only."""

from datetime import date

from django.db import transaction
from django.db.models.functions import Lower

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics import services
from airworthiness_plus.logistics.models import Supplier, SupplierStatus
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.sample.models import Added, Part

EVALUATED_ON = date(2026, 11, 18)
RECORDS = (
    (
        "[Parts Distributor]",
        "Components, Standard Parts and Materials",
        "CAA Form 1 or Certificate of Conformity",
        date(2027, 3, 3),
        "Sample Supplier Evaluation",
    ),
    (
        "[Engine Overhaul Organisation]",
        "Piston Engine Overhaul",
        "CAA Form 1",
        date(2027, 6, 20),
        "Sample Supplier Evaluation",
    ),
    (
        "[Propeller Organisation]",
        "Propeller Overhaul and Repair",
        "CAA Form 1",
        date(2026, 11, 30),
        "Sample Supplier Evaluation",
    ),
    (
        "[Calibration Laboratory]",
        "Tool and Equipment Calibration",
        "Calibration Certificate",
        date(2027, 1, 11),
        "Accredited Laboratory",
    ),
    (
        "[Oil Supplier]",
        "Engine Oil and Grease",
        "Certificate of Conformity",
        None,
        "Batch Without Conformity",
    ),
)


def add(organisation: Organisation, actor: User) -> int:
    """Seed missing sample suppliers once without changing existing records."""
    with working_for(organisation.id, actor.id), transaction.atomic():
        organisation = Organisation.objects.select_for_update(no_key=True).get(pk=organisation.pk)
        if Added.objects.filter(part=Part.SUPPLIERS).exists():
            return 0
        if not any(
            approval.approval == ApprovalType.PART_CAO
            for approval in services.maintenance_approvals(organisation, EVALUATED_ON)
        ):
            return 0
        names = set(
            Supplier.objects.annotate(folded_name=Lower("name")).values_list(
                "folded_name", flat=True
            )
        )
        count = 0
        for name, supplies, documents, deadline, evidence in RECORDS:
            if name.lower() in names:
                continue
            services.record_evaluation(
                organisation,
                name=name,
                approval=ApprovalType.PART_CAO,
                supplies=supplies,
                release_documents=documents,
                evaluated_on=EVALUATED_ON,
                next_evaluation_on=deadline,
                status=SupplierStatus.APPROVED if deadline else SupplierStatus.SUSPENDED,
                evidence=evidence,
            )
            count += 1
        Added.objects.create(organisation=organisation, part=Part.SUPPLIERS)
        return count
